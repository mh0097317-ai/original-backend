# routers/relatorios.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal

from database import AsyncSessionLocal
from models import (
    Movimento, Conta, ContaPagar, ContaReceber,
    TipoMovimento, CategoriaMovimento, StatusMovimento
)
from schemas import FluxoDeCaixaOut, DREOut, ResumoContasOut

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/fluxo-caixa", response_model=list[FluxoDeCaixaOut])
async def fluxo_caixa(
    filial_id: str,
    data_inicio: datetime,
    data_fim: datetime,
    db: AsyncSession = Depends(get_db)
):
    query = select(Movimento).where(
        Movimento.filial_id == filial_id,
        Movimento.data_movimento >= data_inicio,
        Movimento.data_movimento <= data_fim,
        Movimento.status == StatusMovimento.confirmado
    ).order_by(Movimento.data_movimento)

    result = await db.execute(query)
    movimentos = result.scalars().all()

    conta_query = select(Conta).where(Conta.filial_id == filial_id)
    conta_result = await db.execute(conta_query)
    contas = conta_result.scalars().all()

    saldo_inicial = sum(c.saldo_inicial for c in contas)

    fluxo = []
    saldo_atual = saldo_inicial
    data_anterior = data_inicio.date()

    for movimento in movimentos:
        if movimento.data_movimento.date() != data_anterior:
            fluxo.append(FluxoDeCaixaOut(
                data=datetime.combine(data_anterior, datetime.min.time()),
                saldo_inicial=saldo_inicial if data_anterior == data_inicio.date() else saldo_atual,
                entradas=Decimal("0"),
                saidas=Decimal("0"),
                saldo_final=saldo_atual
            ))

        if movimento.tipo == TipoMovimento.entrada:
            saldo_atual += movimento.valor
        else:
            saldo_atual -= movimento.valor

        data_anterior = movimento.data_movimento.date()

    if movimentos:
        fluxo.append(FluxoDeCaixaOut(
            data=datetime.combine(data_anterior, datetime.min.time()),
            saldo_inicial=saldo_inicial if data_anterior == data_inicio.date() else saldo_atual,
            entradas=Decimal("0"),
            saidas=Decimal("0"),
            saldo_final=saldo_atual
        ))

    return fluxo


@router.get("/dre", response_model=DREOut)
async def demonstrativo_resultado(
    filial_id: str,
    mes: int,
    ano: int,
    db: AsyncSession = Depends(get_db)
):
    data_inicio = datetime(ano, mes, 1)
    if mes == 12:
        data_fim = datetime(ano + 1, 1, 1) - timedelta(days=1)
    else:
        data_fim = datetime(ano, mes + 1, 1) - timedelta(days=1)

    query = select(Movimento).where(
        Movimento.filial_id == filial_id,
        Movimento.data_competencia >= data_inicio,
        Movimento.data_competencia <= data_fim,
        Movimento.status == StatusMovimento.confirmado
    )

    result = await db.execute(query)
    movimentos = result.scalars().all()

    receitas_vendas = sum(
        m.valor for m in movimentos
        if m.tipo == TipoMovimento.entrada and m.categoria == CategoriaMovimento.vendas
    )

    despesas_operacionais = sum(
        m.valor for m in movimentos
        if m.tipo == TipoMovimento.saida and m.categoria == CategoriaMovimento.despesa_operacional
    )

    folha_pagamento = sum(
        m.valor for m in movimentos
        if m.tipo == TipoMovimento.saida and m.categoria == CategoriaMovimento.folha_pagamento
    )

    impostos = sum(
        m.valor for m in movimentos
        if m.tipo == TipoMovimento.saida and m.categoria == CategoriaMovimento.impostos
    )

    resultado_liquido = receitas_vendas - despesas_operacionais - folha_pagamento - impostos

    return DREOut(
        periodo=f"{mes:02d}/{ano}",
        receitas_vendas=receitas_vendas,
        despesas_operacionais=despesas_operacionais,
        folha_pagamento=folha_pagamento,
        impostos=impostos,
        resultado_liquido=resultado_liquido
    )


@router.get("/resumo-contas", response_model=ResumoContasOut)
async def resumo_contas(filial_id: str = None, db: AsyncSession = Depends(get_db)):
    query_pagar = select(func.sum(ContaPagar.valor)).where(ContaPagar.pago == False)
    query_receber = select(func.sum(ContaReceber.valor)).where(ContaReceber.recebido == False)

    total_pagar = await db.execute(query_pagar)
    total_receber = await db.execute(query_receber)

    tp = total_pagar.scalar() or Decimal("0")
    tr = total_receber.scalar() or Decimal("0")

    saldo_geral = tr - tp

    vencidas_pagar = await db.execute(
        select(func.count(ContaPagar.id)).where(
            ContaPagar.data_vencimento < datetime.utcnow(),
            ContaPagar.pago == False
        )
    )

    vencidas_receber = await db.execute(
        select(func.count(ContaReceber.id)).where(
            ContaReceber.data_vencimento < datetime.utcnow(),
            ContaReceber.recebido == False
        )
    )

    return ResumoContasOut(
        total_contas_pagar=tp,
        total_contas_receber=tr,
        saldo_geral=saldo_geral,
        contas_pagar_vencidas=vencidas_pagar.scalar() or 0,
        contas_receber_vencidas=vencidas_receber.scalar() or 0
    )


@router.get("/saldo-contas")
async def saldo_contas(filial_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Conta).where(Conta.filial_id == filial_id, Conta.ativa == True)
    result = await db.execute(query)
    contas = result.scalars().all()

    return {
        "saldo_total": sum(c.saldo_atual for c in contas),
        "contas": [
            {
                "id": c.id,
                "nome": c.nome,
                "tipo": c.tipo.value,
                "saldo": float(c.saldo_atual)
            }
            for c in contas
        ]
    }
