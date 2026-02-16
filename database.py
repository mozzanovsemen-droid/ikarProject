from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn

engiene = create_async_engine(
    "sqlite+aiosqlite:///tasks.db"
)

new_session = async_sessionmaker(engiene, expire_on_commit=False)

class Model(DeclarativeBase):
    pass


class TasksOrm(Model):
    __tablename__ = "tasks"

    id: Mapped[int] = MappedColumn(primary_key=True)
    name: Mapped[str]
    description: Mapped[Optional[str]]

async def create_tables():
    async with engiene.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

async def delete_tables():
    async with engiene.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)