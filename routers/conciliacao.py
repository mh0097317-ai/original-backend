# routers/conciliacao.py
"""Conciliação bancária via Pluggy (Open Finance).

Fluxo: conectar banco (widget Pluggy Connect) → vincular conta →
importar extrato → conciliar automaticamente → resolver divergências
(conciliar manual, lançar no caixa ou ignorar).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    Conta, Movimento, ConexaoBancaria, TransacaoBancaria, Usuario,
    TipoMovimento, StatusMovimento, StatusConciliacao, AcaoAudit,
)
from schemas import (
    ConexaoBancariaCriar, ConexaoBancariaOut, TransacaoBancariaOut,
    ImportarExtratoIn, ImportacaoOut, ConciliacaoResultadoOut,
    ConciliarManualIn, LancarTransacaoIn, ConnectTokenOut,
    ResumoConciliacaoOut, Pagina,
)
from security import get_usuario_atual, requer_gestor, registrar_audit, filial_permitida
from pluggy_client import PluggyClient, get_pluggy_client
from routers.movimentos import _aplicar_no_saldo

router = APIRouter(prefix="/api/conciliacao", tags=["Conciliação Bancária"])


# ── Conexões ──────────────────────────────────────────────
@router.post("/connect-token", response_model=ConnectTokenOut)
async def connect_token(
    usuario: Usuario = Depends(requer_gestor),
    pluggy: PluggyClient = Depends(get_pluggy_client),
):
    """Token para abrir o widget Pluggy Connect no app/site e conectar o banco."""
    token = await pluggy.criar_connect_token()
    return ConnectTokenOut(access_token=token)


@router.post("/conexoes", response_model=ConexaoBancariaOut, status_code=status.HTTP_201_CREATED)
async def criar_conexao(
    dados: ConexaoBancariaCriar,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    conta = (await db.execute(select(Conta).where(Conta.id == dados.conta_id))).scalar_one_or_none()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if not filial_permitida(usuario, conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conta")

    existe = (await db.execute(
        select(ConexaoBancaria).where(
            ConexaoBancaria.conta_id == dados.conta_id,
            ConexaoBancaria.ativa == True,  # noqa: E712
        )
    )).scalar_one_or_none()
    if existe:
        raise HTTPException(status_code=400, detail="Conta já possui conexão bancária ativa")

    conexao = ConexaoBancaria(**dados.model_dump(), filial_id=conta.filial_id)
    db.add(conexao)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.criar, "conexao_bancaria", conexao.id,
                          {"conta_id": conexao.conta_id, "banco": conexao.banco_nome})
    return conexao


@router.get("/conexoes", response_model=Pagina[ConexaoBancariaOut])
async def listar_conexoes(
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cond = []
    if usuario.filial_id and usuario.role.value != "admin":
        cond.append(ConexaoBancaria.filial_id == usuario.filial_id)
    total = await db.execute(select(func.count(ConexaoBancaria.id)).where(*cond))
    result = await db.execute(select(ConexaoBancaria).where(*cond).offset(skip).limit(limit))
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


async def _obter_conexao(db: AsyncSession, usuario: Usuario, conexao_id: str) -> ConexaoBancaria:
    conexao = (await db.execute(
        select(ConexaoBancaria).where(ConexaoBancaria.id == conexao_id)
    )).scalar_one_or_none()
    if not conexao:
        raise HTTPException(status_code=404, detail="Conexão bancária não encontrada")
    if not filial_permitida(usuario, conexao.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta conexão")
    return conexao


# ── Importação do extrato ─────────────────────────────────
def _parse_transacao_pluggy(t: dict) -> dict:
    """Normaliza uma transação do Pluggy para o nosso modelo."""
    amount = Decimal(str(t["amount"]))
    tipo_raw = (t.get("type") or "").upper()
    if tipo_raw == "CREDIT":
        tipo = TipoMovimento.entrada
    elif tipo_raw == "DEBIT":
        tipo = TipoMovimento.saida
    else:
        tipo = TipoMovimento.entrada if amount >= 0 else TipoMovimento.saida
    data = datetime.fromisoformat(t["date"].replace("Z", "+00:00")).replace(tzinfo=None)
    return {
        "pluggy_transaction_id": str(t["id"]),
        "descricao": (t.get("description") or "Transação bancária")[:300],
        "tipo": tipo,
        "valor": abs(amount).quantize(Decimal("0.01")),
        "data": data,
    }


@router.post("/conexoes/{conexao_id}/importar", response_model=ImportacaoOut)
async def importar_extrato(
    conexao_id: str,
    periodo: ImportarExtratoIn,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
    pluggy: PluggyClient = Depends(get_pluggy_client),
):
    """Busca o extrato no banco (via Pluggy) e grava as transações novas."""
    conexao = await _obter_conexao(db, usuario, conexao_id)

    brutas = await pluggy.transacoes(conexao.pluggy_account_id,
                                     periodo.data_inicio, periodo.data_fim)

    ids = [str(t["id"]) for t in brutas]
    existentes = set()
    if ids:
        rows = await db.execute(
            select(TransacaoBancaria.pluggy_transaction_id)
            .where(TransacaoBancaria.pluggy_transaction_id.in_(ids))
        )
        existentes = {r[0] for r in rows.all()}

    novas = 0
    for t in brutas:
        if str(t["id"]) in existentes:
            continue
        db.add(TransacaoBancaria(
            **_parse_transacao_pluggy(t),
            conexao_id=conexao.id,
            conta_id=conexao.conta_id,
        ))
        novas += 1

    conexao.ultima_importacao = datetime.utcnow()
    db.add(conexao)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.importar, "conexao_bancaria", conexao.id,
                          {"importadas": novas, "ja_existentes": len(existentes)})
    return ImportacaoOut(importadas=novas, ja_existentes=len(existentes))


# ── Motor de conciliação automática ───────────────────────
@router.post("/conexoes/{conexao_id}/conciliar", response_model=ConciliacaoResultadoOut)
async def conciliar_automatico(
    conexao_id: str,
    janela_dias: int = Query(3, ge=0, le=15),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    """Casa transações do extrato com movimentos do caixa.

    Critério: mesma conta, mesmo tipo, mesmo valor e data dentro da janela
    (± janela_dias). Cada movimento só concilia com uma transação. O que
    sobrar vira 'divergente' — dinheiro que passou no banco sem lançamento
    no caixa (ou vice-versa).
    """
    conexao = await _obter_conexao(db, usuario, conexao_id)

    pendentes = (await db.execute(
        select(TransacaoBancaria).where(
            TransacaoBancaria.conexao_id == conexao.id,
            TransacaoBancaria.status_conciliacao.in_(
                [StatusConciliacao.pendente, StatusConciliacao.divergente]
            ),
        ).order_by(TransacaoBancaria.data)
    )).scalars().all()

    # movimentos já usados por outras conciliações não podem casar de novo
    usados_rows = await db.execute(
        select(TransacaoBancaria.movimento_id)
        .where(TransacaoBancaria.movimento_id.is_not(None))
    )
    usados = {r[0] for r in usados_rows.all()}

    movimentos = (await db.execute(
        select(Movimento).where(
            Movimento.conta_id == conexao.conta_id,
            Movimento.status == StatusMovimento.confirmado,
        )
    )).scalars().all()
    candidatos = [m for m in movimentos if m.id not in usados]

    conciliadas = divergentes = 0
    janela = timedelta(days=janela_dias)
    for trans in pendentes:
        match = None
        for mov in candidatos:
            if (mov.tipo == trans.tipo
                    and mov.valor == trans.valor
                    and abs(mov.data_movimento - trans.data) <= janela):
                match = mov
                break
        if match:
            trans.status_conciliacao = StatusConciliacao.conciliado
            trans.movimento_id = match.id
            candidatos.remove(match)
            conciliadas += 1
        else:
            trans.status_conciliacao = StatusConciliacao.divergente
            divergentes += 1
        db.add(trans)

    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.conciliar, "conexao_bancaria", conexao.id,
                          {"conciliadas": conciliadas, "divergentes": divergentes})

    restantes = (await db.execute(
        select(func.count(TransacaoBancaria.id)).where(
            TransacaoBancaria.conexao_id == conexao.id,
            TransacaoBancaria.status_conciliacao == StatusConciliacao.pendente,
        )
    )).scalar()
    return ConciliacaoResultadoOut(conciliadas=conciliadas, divergentes=divergentes,
                                   pendentes=restantes or 0)


# ── Transações e resolução de divergências ────────────────
@router.get("/transacoes", response_model=Pagina[TransacaoBancariaOut])
async def listar_transacoes(
    conta_id: str | None = None,
    situacao: StatusConciliacao | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cond = []
    if conta_id:
        cond.append(TransacaoBancaria.conta_id == conta_id)
    if situacao:
        cond.append(TransacaoBancaria.status_conciliacao == situacao)
    if usuario.filial_id and usuario.role.value != "admin":
        contas_filial = select(Conta.id).where(Conta.filial_id == usuario.filial_id)
        cond.append(TransacaoBancaria.conta_id.in_(contas_filial))

    total = await db.execute(select(func.count(TransacaoBancaria.id)).where(*cond))
    result = await db.execute(
        select(TransacaoBancaria).where(*cond)
        .order_by(TransacaoBancaria.data.desc()).offset(skip).limit(limit)
    )
    return Pagina(total=total.scalar() or 0, skip=skip, limit=limit,
                  items=list(result.scalars().all()))


async def _obter_transacao(db: AsyncSession, usuario: Usuario, transacao_id: str) -> TransacaoBancaria:
    trans = (await db.execute(
        select(TransacaoBancaria).where(TransacaoBancaria.id == transacao_id)
    )).scalar_one_or_none()
    if not trans:
        raise HTTPException(status_code=404, detail="Transação bancária não encontrada")
    conta = (await db.execute(select(Conta).where(Conta.id == trans.conta_id))).scalar_one()
    if not filial_permitida(usuario, conta.filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta transação")
    return trans


@router.post("/transacoes/{transacao_id}/conciliar-manual", response_model=TransacaoBancariaOut)
async def conciliar_manual(
    transacao_id: str,
    dados: ConciliarManualIn,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    trans = await _obter_transacao(db, usuario, transacao_id)
    if trans.status_conciliacao == StatusConciliacao.conciliado:
        raise HTTPException(status_code=400, detail="Transação já conciliada")

    mov = (await db.execute(
        select(Movimento).where(Movimento.id == dados.movimento_id)
    )).scalar_one_or_none()
    if not mov or mov.conta_id != trans.conta_id:
        raise HTTPException(status_code=404, detail="Movimento não encontrado nesta conta")
    if mov.status != StatusMovimento.confirmado:
        raise HTTPException(status_code=400, detail="Movimento não está confirmado")

    ja_usado = (await db.execute(
        select(TransacaoBancaria).where(TransacaoBancaria.movimento_id == mov.id)
    )).scalar_one_or_none()
    if ja_usado:
        raise HTTPException(status_code=400, detail="Movimento já conciliado com outra transação")

    trans.status_conciliacao = StatusConciliacao.conciliado
    trans.movimento_id = mov.id
    db.add(trans)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.conciliar, "transacao_bancaria", trans.id,
                          {"movimento_id": mov.id, "manual": True})
    return trans


@router.post("/transacoes/{transacao_id}/lancar", response_model=TransacaoBancariaOut)
async def lancar_no_caixa(
    transacao_id: str,
    dados: LancarTransacaoIn,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    """Cria o movimento de caixa a partir da transação do banco e concilia.

    O extrato é fato consumado — o lançamento é criado mesmo que deixe o
    saldo negativo (diferente do lançamento manual, que bloqueia).
    """
    trans = await _obter_transacao(db, usuario, transacao_id)
    if trans.status_conciliacao == StatusConciliacao.conciliado:
        raise HTTPException(status_code=400, detail="Transação já conciliada")

    conta = (await db.execute(select(Conta).where(Conta.id == trans.conta_id))).scalar_one()

    mov = Movimento(
        filial_id=conta.filial_id,
        conta_id=conta.id,
        tipo=trans.tipo,
        categoria=dados.categoria,
        descricao=dados.descricao or f"[Banco] {trans.descricao}",
        valor=trans.valor,
        data_movimento=trans.data,
        data_competencia=trans.data,
        status=StatusMovimento.confirmado,
        criado_por=usuario.id,
    )
    db.add(mov)
    _aplicar_no_saldo(conta, mov)
    db.add(conta)
    await db.flush()

    trans.status_conciliacao = StatusConciliacao.conciliado
    trans.movimento_id = mov.id
    db.add(trans)
    await db.flush()
    await registrar_audit(db, usuario, AcaoAudit.conciliar, "transacao_bancaria", trans.id,
                          {"movimento_id": mov.id, "lancado_do_extrato": True})
    return trans


@router.post("/transacoes/{transacao_id}/ignorar", response_model=TransacaoBancariaOut)
async def ignorar_transacao(
    transacao_id: str,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(requer_gestor),
):
    trans = await _obter_transacao(db, usuario, transacao_id)
    if trans.status_conciliacao == StatusConciliacao.conciliado:
        raise HTTPException(status_code=400, detail="Transação já conciliada")
    trans.status_conciliacao = StatusConciliacao.ignorado
    db.add(trans)
    await registrar_audit(db, usuario, AcaoAudit.conciliar, "transacao_bancaria", trans.id,
                          {"ignorada": True})
    return trans


@router.get("/resumo", response_model=ResumoConciliacaoOut)
async def resumo_conciliacao(
    conta_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cond = []
    if conta_id:
        cond.append(TransacaoBancaria.conta_id == conta_id)
    if usuario.filial_id and usuario.role.value != "admin":
        contas_filial = select(Conta.id).where(Conta.filial_id == usuario.filial_id)
        cond.append(TransacaoBancaria.conta_id.in_(contas_filial))

    async def contar(*extra):
        r = await db.execute(select(func.count(TransacaoBancaria.id)).where(*cond, *extra))
        return r.scalar() or 0

    return ResumoConciliacaoOut(
        total=await contar(),
        conciliadas=await contar(TransacaoBancaria.status_conciliacao == StatusConciliacao.conciliado),
        divergentes=await contar(TransacaoBancaria.status_conciliacao == StatusConciliacao.divergente),
        pendentes=await contar(TransacaoBancaria.status_conciliacao == StatusConciliacao.pendente),
        ignoradas=await contar(TransacaoBancaria.status_conciliacao == StatusConciliacao.ignorado),
    )
