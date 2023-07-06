from typing import Annotated, Any, AsyncGenerator
from fastapi import Depends


from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


from config import get_settings


DATABASE_URL = f"postgresql+asyncpg://{get_settings().postgres_user}:{get_settings().postgres_password}@postgres/{get_settings().postgres_db}"


class Base(AsyncAttrs, DeclarativeBase):
    def repr_dict(self) -> dict[str, Any]:
        raise NotImplementedError()

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        fields = self.repr_dict()
        fields_string = ", ".join([f"{key}={value}" for (key, value) in fields.items()])
        return f"{class_name}({fields_string})"


engine = create_async_engine(DATABASE_URL)
session_maker = async_sessionmaker(engine, expire_on_commit=False)


# TODO: replace with alembic
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # await conn.execute(
        #    Artist.insert(), [{"name": "some name 1"}, {"name": "some name 2"}]
        # )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        yield session


DbSessionDependency = Annotated[AsyncSession, Depends(get_session)]
