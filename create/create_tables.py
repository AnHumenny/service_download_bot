import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from schemas.database import DATABASE_URL, Model


async def create_tables():
    """Создание всех таблиц"""
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        print("Таблицы успешно созданы!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
