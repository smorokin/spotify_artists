from base64 import b64encode
import secrets
import string
from logging import getLogger
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from httpx import AsyncClient
from pydantic import ValidationError, parse_obj_as

from config import SettingsDependency
from db import DbSessionDependency, create_db_and_tables
import schemas
import crud

_logger = getLogger(__file__)

app = FastAPI()


@app.on_event("startup")
async def startup():
    await create_db_and_tables()


@app.on_event("shutdown")
async def shutdown():
    pass


@app.get("/login")
async def login(settings: SettingsDependency) -> RedirectResponse:
    state = "".join(
        secrets.choice(string.ascii_uppercase + string.ascii_lowercase)
        for i in range(16)
    )
    async with AsyncClient() as client:
        reply = await client.get(
            "https://accounts.spotify.com/authorize",
            params={
                "client_id": settings.spotify_client_id,
                "response_type": "code",
                "scope": "user-read-private user-read-email",
                "redirect_uri": "http://localhost:8000/login_response",
                "state": state,
            },
            follow_redirects=True,
        )
        # using a redirect response here so it will work with just the backend
        response = RedirectResponse(str(reply.url))
        # add state as cookie for later check
        response.set_cookie("orignial_state", state)

        return response


@app.get("/login_response")
async def login_response(
    settings: SettingsDependency,
    db_session: DbSessionDependency,
    request: Request,
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> str:
    original_state = request.cookies.get("orignial_state")
    if original_state != state:
        _logger.error("login call had mismatched state")
        return "state_mismatch"
    if error is not None:
        _logger.error("login call retured error %s", error)
        return error
    if code is None:
        _logger.error("login call retured no code")
        return "no_code"

    auth = b64encode(
        settings.spotify_client_id.encode()
        + b":"
        + settings.spotify_client_secret.encode()
    ).decode("utf-8")

    async with AsyncClient() as client:
        reply = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:8000/login_response",
            },
            headers={
                "Authorization": f"Basic {settings.to_auth_header()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            follow_redirects=True,
        )
        if reply.is_error:
            _logger.error("getting auth tokens failed. Reply was %s", reply)
            return "get_tokens_failed"

        reply_json = reply.json()
        try:
            tokens = schemas.AuthToken.validate(reply_json)
            await crud.replace_auth_token(db_session, tokens)

            return "login_successful"

        except ValidationError as e:
            _logger.error("parsing auth tokens failed with error %s", e)
            return "parsing_tokens_failed"


@app.get("/auth_token")
async def auth_token(
    db_session: DbSessionDependency,
) -> schemas.AuthToken | None:
    return await crud.read_auth_token(db_session)


@app.get("/refresh_auth_token")
async def refresh_auth_token(
    settings: SettingsDependency, db_session: DbSessionDependency
) -> schemas.AuthToken | None:
    old_tokens = await crud.read_auth_token(db_session)

    if old_tokens is None:
        _logger.warning("no auth tokens present")
        return

    if old_tokens.expired():
        _logger.warning("auth tokens expired")
        return

    async with AsyncClient() as client:
        reply = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": old_tokens.refresh_token,
            },
            headers={
                "Authorization": f"Basic {settings.to_auth_header()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            follow_redirects=True,
        )
        if reply.is_error:
            _logger.error("getting auth tokens failed. Reply was %s", reply)
            return

        reply_json = reply.json()
        try:
            reply_json["refresh_token"] = old_tokens.refresh_token

            new_token = schemas.AuthToken.validate(reply_json)
            await crud.replace_auth_token(db_session, new_token)
            return new_token

        except ValidationError as e:
            _logger.error("parsing auth tokens failed with error %s", e)


@app.get("/update_artists_from_spotify")
async def update_artists_from_spotify(
    settings: SettingsDependency, db_session: DbSessionDependency
) -> list[schemas.Artist]:
    auth_token = await crud.read_auth_token(db_session)
    if auth_token is None:
        _logger.error(
            "getting artists failed. No auth token. Please login first (visit /login)"
        )
        return []

    async with AsyncClient() as client:
        reply = await client.get(
            "https://api.spotify.com/v1/artists",
            params={"ids": ",".join(settings.artists_to_track)},
            headers={"Authorization": f"Bearer {auth_token.access_token}"},
            follow_redirects=True,
        )
        if reply.is_error:
            _logger.error("getting artists failed. Reply was %s", reply)
            return []

        reply_json = reply.json()
        try:
            artists = parse_obj_as(list[schemas.Artist], reply_json.get("artists"))
            _logger.debug("got artists %s", artists)
            await crud.update_artists(db_session, artists)
            return artists

        except ValidationError as e:
            _logger.error("parsing artists failed with error %s", e)
            return []


@app.get("/artist/{artist_id}")
async def get_artist(
    db_session: DbSessionDependency, artist_id: str
) -> schemas.Artist | None:
    return await crud.read_artist(db_session, artist_id)


@app.put("/artist/{artist_id}")
async def update_artist(
    db_session: DbSessionDependency, artist_id: str, artist: schemas.Artist
) -> schemas.Artist | None:
    return await crud.update_artist(db_session, artist, False, True)
