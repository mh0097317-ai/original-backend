# routers/veiculos.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Veiculo, Categoria, CategoriaEnum, StatusVeiculoEnum
from schemas import VeiculoOut, CategoriaOut

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.get("/", response_model=List[VeiculoOut])
async def listar_veiculos(
    categoria: Optional[CategoriaEnum] = Query(None, description="Filtrar por categoria"),
    disponivel: bool = Query(True, description="Apenas disponíveis"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Veiculo).order_by(Veiculo.nota_media.desc())

    if disponivel:
        query = query.where(Veiculo.status == StatusVeiculoEnum.disponivel)
    if categoria:
        query = query.where(Veiculo.categoria == categoria)

    result = await db.execute(query)
    return [VeiculoOut.model_validate(v) for v in result.scalars().all()]


@router.get("/{veiculo_id}", response_model=VeiculoOut)
async def buscar_veiculo(veiculo_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Veiculo).where(Veiculo.id == veiculo_id))
    veiculo = result.scalar_one_or_none()
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado")
    return VeiculoOut.model_validate(veiculo)


@router.get("/categorias/todas", response_model=List[CategoriaOut])
async def listar_categorias(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Categoria).order_by(Categoria.slug))
    return [CategoriaOut.model_validate(c) for c in result.scalars().all()]
