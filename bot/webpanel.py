from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import load_config
from .db import get_session, init_db
from .models import Manager, Client, Order, OrderStatus, Direction

app = FastAPI(title="Oplatym CRM Admin Panel")
cfg = load_config()


async def get_db() -> AsyncSession:
    async for s in get_session():
        yield s


def check_token(token: str):
    if token != cfg.admin_panel_token:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/stats/summary")
async def stats_summary(token: str, db: AsyncSession = Depends(get_db)):
    check_token(token)

    total_clients = (await db.execute(select(func.count(Client.id)))).scalar_one()
    total_managers = (await db.execute(select(func.count(Manager.id)))).scalar_one()
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar_one()
    total_active = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.active))).scalar_one()
    total_closed = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.closed))).scalar_one()
    total_amount = (await db.execute(select(func.coalesce(func.sum(Order.amount), 0)))).scalar_one()

    return {
        "total_clients": total_clients,
        "total_managers": total_managers,
        "total_orders": total_orders,
        "total_active_orders": total_active,
        "total_closed_orders": total_closed,
        "total_amount": float(total_amount),
    }


@app.get("/stats/by-direction")
async def stats_by_direction(token: str, db: AsyncSession = Depends(get_db)):
    check_token(token)

    rows = (
        await db.execute(
            select(Order.direction, func.count(Order.id), func.coalesce(func.sum(Order.amount), 0))
            .group_by(Order.direction)
        )
    ).all()

    data = []
    for direction, count, amount in rows:
        data.append({
            "direction": direction.value if direction else None,
            "orders": count,
            "amount": float(amount),
        })

    return data


@app.get("/stats/by-manager")
async def stats_by_manager(token: str, db: AsyncSession = Depends(get_db)):
    check_token(token)

    rows = (
        await db.execute(
            select(
                Manager.id,
                Manager.first_name,
                func.count(Order.id),
                func.coalesce(func.sum(Order.amount), 0),
            )
            .outerjoin(Order, Order.manager_id == Manager.id)
            .group_by(Manager.id, Manager.first_name)
        )
    ).all()

    data = []
    for mid, name, count, amount in rows:
        data.append({
            "manager_id": mid,
            "name": name,
            "orders": count,
            "amount": float(amount),
        })

    return data
