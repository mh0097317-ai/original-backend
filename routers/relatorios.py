# routers/relatorios.py
from collections import OrderedDict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal

from database import get_db
from models import (
    Movimento, Conta, ContaPagar, ContaReceber, Usuario,
    TipoMovimento, CategoriaMovimento, StatusMovimento,
)
from schemas import FluxoDeCaixaOut, DREOut, ResumoContasOut
from security import get_usuario_atual, filial_permitida

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])

ZERO = Decimal("0.00")


def _checar_acesso(usuario: Usuario, filial_id: str):
    if not filial_permitida(usuario, filial_id):
        raise HTTPException(status_code=403, detail="Sem acesso a esta filial")


@router.get("/fluxo-caixa", response_model=list[FluxoDeCaixaOut])
async def fluxo_caixa(
    filial_id: str,
    data_inicio: datetime,
    data_fim: datetime,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    """Fluxo de caixa diário: saldo de abertura, entradas, saídas e saldo final por dia."""
    _checar_acesso(usuario, filial_id)

    # Saldo de abertura = saldo inicial das contas + movimentos confirmados antes do período
    contas = await db.execute(select(Conta).where(Conta.filial_id == filial_id))
    saldo_abertura = sum((c.saldo_inicial for c in contas.scalars().all()), ZERO)

    anteriores = await db.execute(
        select(Movimento).where(
            Movimento.filial_id == filial_id,
            Movimento.status == StatusMovimento.confirmado,
            Movimento.data_movimento < data_inicio,
        )
    )
    for m in anteriores.scalars().all():
        saldo_abertura += m.valor if m.tipo == TipoMovimento.entrada else -m.valor

    # Movimentos do período agrupados por dia
    result = await db.execute(
        select(Movimento).where(
            Movimento.filial_id == filial_id,
            Movimento.status == StatusMovimento.confirmado,
            Movimento.data_movimento >= data_inicio,
            Movimento.data_movimento <= data_fim,
        ).order_by(Movimento.data_movimento)
    )
    por_dia: "OrderedDict[datetime, dict]" = OrderedDict()
    for m in result.scalars().all():
        dia = datetime.combine(m.data_movimento.date(), datetime.min.time())
        bucket = por_dia.setdefault(dia, {"entradas": ZERO, "saidas": ZERO})
        if m.tipo == TipoMovimento.entrada:
            bucket["entradas"] += m.valor
        else:
            bucket["saidas"] += m.valor

    fluxo = []
    saldo_corrente = saldo_abertura
    for dia, vals in por_dia.items():
        inicial = saldo_corrente
        final = inicial + vals["entradas"] - vals["saidas"]
        fluxo.append(FluxoDeCaixaOut(
            data=dia,
            saldo_inicial=inicial,
            entradas=vals["entradas"],
            saidas=vals["saidas"],
            saldo_final=final,
        ))
        saldo_corrente = final

    return fluxo


@router.get("/dre", response_model=DREOut)
async def demonstrativo_resultado(
    filial_id: str,
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    _checar_acesso(usuario, filial_id)
    if not 1 <= mes <= 12:
        raise HTTPException(status_code=400, detail="Mês inválido")

    data_inicio = datetime(ano, mes, 1)
    data_fim = (datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)) - timedelta(seconds=1)

    result = await db.execute(
        select(Movimento).where(
            Movimento.filial_id == filial_id,
            Movimento.status == StatusMovimento.confirmado,
            Movimento.data_competencia >= data_inicio,
            Movimento.data_competencia <= data_fim,
        )
    )
    movs = result.scalars().all()

    def soma(tipo, categoria):
        return sum((m.valor for m in movs if m.tipo == tipo and m.categoria == categoria), ZERO)

    receitas = soma(TipoMovimento.entrada, CategoriaMovimento.vendas)
    despesas = soma(TipoMovimento.saida, CategoriaMovimento.despesa_operacional)
    folha = soma(TipoMovimento.saida, CategoriaMovimento.folha_pagamento)
    impostos = soma(TipoMovimento.saida, CategoriaMovimento.impostos)
    resultado = receitas - despesas - folha - impostos

    return DREOut(
        periodo=f"{mes:02d}/{ano}",
        receitas_vendas=receitas,
        despesas_operacionais=despesas,
        folha_pagamento=folha,
        impostos=impostos,
        resultado_liquido=resultado,
    )


@router.get("/resumo-contas", response_model=ResumoContasOut)
async def resumo_contas(db: AsyncSession = Depends(get_db), usuario: Usuario = Depends(get_usuario_atual)):
    total_pagar = (await db.execute(
        select(func.coalesce(func.sum(ContaPagar.valor), 0)).where(ContaPagar.pago == False)  # noqa: E712
    )).scalar()
    total_receber = (await db.execute(
        select(func.coalesce(func.sum(ContaReceber.valor), 0)).where(ContaReceber.recebido == False)  # noqa: E712
    )).scalar()

    tp = Decimal(str(total_pagar or 0))
    tr = Decimal(str(total_receber or 0))

    venc_pagar = (await db.execute(
        select(func.count(ContaPagar.id)).where(
            ContaPagar.data_vencimento < datetime.utcnow(),
            ContaPagar.pago == False,  # noqa: E712
        )
    )).scalar()
    venc_receber = (await db.execute(
        select(func.count(ContaReceber.id)).where(
            ContaReceber.data_vencimento < datetime.utcnow(),
            ContaReceber.recebido == False,  # noqa: E712
        )
    )).scalar()

    return ResumoContasOut(
        total_contas_pagar=tp,
        total_contas_receber=tr,
        saldo_geral=tr - tp,
        contas_pagar_vencidas=venc_pagar or 0,
        contas_receber_vencidas=venc_receber or 0,
    )


@router.get("/saldo-contas")
async def saldo_contas(filial_id: str, db: AsyncSession = Depends(get_db),
                       usuario: Usuario = Depends(get_usuario_atual)):
    _checar_acesso(usuario, filial_id)
    result = await db.execute(
        select(Conta).where(Conta.filial_id == filial_id, Conta.ativa == True)  # noqa: E712
    )
    contas = result.scalars().all()
    return {
        "filial_id": filial_id,
        "saldo_total": float(sum((c.saldo_atual for c in contas), ZERO)),
        "contas": [
            {"id": c.id, "nome": c.nome, "tipo": c.tipo.value, "saldo": float(c.saldo_atual)}
            for c in contas
        ],
    }
