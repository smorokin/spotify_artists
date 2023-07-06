from base64 import b64encode
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from pydantic import BaseSettings


class Settings(BaseSettings):
    postgres_db: str
    postgres_user: str
    postgres_password: str

    celery_broker_url: str
    celery_result_backend: str

    spotify_client_id: str
    spotify_client_secret: str

    artists_to_track: list[str]

    def to_auth_header(self) -> str:
        return b64encode(
            self.spotify_client_id.encode() + b":" + self.spotify_client_secret.encode()
        ).decode("utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore , false negative since settings are loaded from environment vars


SettingsDependency = Annotated[Settings, Depends(get_settings)]
