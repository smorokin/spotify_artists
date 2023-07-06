from logging import getLogger

from celery import Celery
from httpx import AsyncClient
from pydantic import ValidationError, parse_obj_as

from config import get_settings
import crud
import main
from db import get_session
from schemas import AuthToken, Artist

_logger = getLogger(__file__)

celery = Celery(
    __name__,
    broker=get_settings().celery_broker_url,
    result_backend=get_settings().celery_result_backend,
)


@celery.on_after_configure.connect  # type: ignore
def setup_periodic_tasks(sender: Celery, **kwargs) -> None:
    sender.add_periodic_task(
        600.0, update_artists.s(), name="update artists every 10 mins"
    )

    sender.add_periodic_task(
        300.0, refresh_token.s(), name="check refresh token every 5 mins"
    )


@celery.task(name="update_artists")
async def update_artists() -> None:
    _logger.info("running update_artists")
    settings = get_settings()
    db_session = await anext(get_session())
    await main.update_artists_from_spotify(settings, db_session)


@celery.task(name="refresh_token")
async def refresh_token() -> None:
    _logger.info("running refresh_token")
    settings = get_settings()
    db_session = await anext(get_session())
    await main.refresh_auth_token(settings, db_session)
