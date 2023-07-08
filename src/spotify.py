from logging import getLogger
from typing import Annotated
from fastapi import Depends
from httpx import AsyncClient
from pydantic import AnyHttpUrl, parse_obj_as
import schemas


_logger = getLogger(__file__)


class SpotifyClient:
    @staticmethod
    async def login(client_id: str, base_url: AnyHttpUrl, state: str) -> AnyHttpUrl:
        async with AsyncClient() as client:
            reply = await client.get(
                "https://accounts.spotify.com/authorize",
                params={
                    "client_id": client_id,
                    "response_type": "code",
                    "scope": "user-read-private user-read-email",
                    "redirect_uri": f"{base_url}/login_response",
                    "state": state,
                },
                follow_redirects=True,
            )
        url_str = str(reply.url)
        return parse_obj_as(AnyHttpUrl, url_str)

    @staticmethod
    async def get_token(
        base_url: AnyHttpUrl, auth_header: str, code: str
    ) -> schemas.AuthToken | None:
        async with AsyncClient() as client:
            reply = await client.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{base_url}/login_response",
                },
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                follow_redirects=True,
            )
        if reply.is_error:
            _logger.error("getting auth tokens failed. Reply was %s", reply)

        reply_json = reply.json()

        return schemas.AuthToken.validate(reply_json)

    @staticmethod
    async def refresh_token(
        old_token: schemas.AuthToken, auth_header: str
    ) -> schemas.AuthToken | None:
        async with AsyncClient() as client:
            reply = await client.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": old_token.refresh_token,
                },
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                follow_redirects=True,
            )
        if reply.is_error:
            _logger.error("getting auth tokens failed. Reply was %s", reply)
            return

        reply_json = reply.json()
        reply_json["refresh_token"] = old_token.refresh_token
        return schemas.AuthToken.validate(reply_json)

    @staticmethod
    async def get_artists(
        artist_ids: list[str], auth_token: schemas.AuthToken
    ) -> list[schemas.Artist]:
        async with AsyncClient() as client:
            reply = await client.get(
                "https://api.spotify.com/v1/artists",
                params={"ids": ",".join(artist_ids)},
                headers={"Authorization": f"Bearer {auth_token.access_token}"},
                follow_redirects=True,
            )
        if reply.is_error:
            _logger.error("getting artists failed. Reply was %s", reply)
            return []

        reply_json = reply.json()

        artists = parse_obj_as(list[schemas.Artist], reply_json.get("artists"))
        _logger.debug("got artists %s", artists)
        return artists


SpotifyClientDependency = Annotated[SpotifyClient, Depends(SpotifyClient)]
