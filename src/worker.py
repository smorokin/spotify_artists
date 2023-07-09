from typing import AsyncGenerator
from logging import getLogger
import asyncio

from celery import Celery
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import get_settings
import main
from db import DATABASE_URL
from crud import ArtistCrud, AuthTokenCrud
from spotify import SpotifyClient

_logger = getLogger(__file__)

celery = Celery(
    __name__,
    broker=get_settings().celery_broker_url,
    result_backend=get_settings().celery_result_backend,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


event_loop = asyncio.get_event_loop()


@celery.on_after_configure.connect  # type: ignore
def setup_periodic_tasks(sender: Celery, **kwargs) -> None:
    sender.add_periodic_task(60.0, update_artists.s(), name="update artists")

    sender.add_periodic_task(30.0, refresh_token.s(), name="check refresh token")


@celery.task(name="update_artists")
def update_artists() -> None:
    asyncio.ensure_future(_update_artists(), loop=event_loop)


async def _update_artists() -> None:
    _logger.info("running update_artists")
    settings = get_settings()
    db_session = await anext(get_session())
    auth_token_crud = AuthTokenCrud()
    artist_crud = ArtistCrud()
    spotify_client = SpotifyClient()
    await main.update_artists_from_spotify(
        settings, db_session, auth_token_crud, artist_crud, spotify_client
    )


@celery.task(name="refresh_token")
def refresh_token() -> None:
    asyncio.ensure_future(_refresh_token(), loop=event_loop)


async def _refresh_token() -> None:
    _logger.info("running refresh_token")
    loop2 = asyncio.get_event_loop()
    print(loop2)
    settings = get_settings()
    db_session = await anext(get_session())
    auth_token_crud = AuthTokenCrud()
    spotify_client = SpotifyClient()
    await main.refresh_auth_token(settings, db_session, auth_token_crud, spotify_client)
