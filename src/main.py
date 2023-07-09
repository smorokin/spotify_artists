import secrets
import string
from logging import getLogger
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from config import SettingsDependency
from db import DbSessionDependency, create_db_and_tables
import schemas
from crud import AuthTokenCrudDependency, ArtistCrudDependency
from spotify import SpotifyClientDependency

_logger = getLogger(__file__)

app = FastAPI()


@app.on_event("startup")
async def startup():
    await create_db_and_tables()


@app.on_event("shutdown")
async def shutdown():
    pass


@app.get("/")
async def root():
    return {"msg": "Hello World"}


@app.get("/login")
async def login(
    settings: SettingsDependency, spotify_client: SpotifyClientDependency
) -> RedirectResponse:
    """Login to Spotify (sadly does not work from Swagger)"""
    state = "".join(
        secrets.choice(string.ascii_uppercase + string.ascii_lowercase)
        for _ in range(16)
    )
    reply_url = await spotify_client.login(
        settings.spotify_client_id, settings.base_url, state
    )
    print(reply_url)

    # using a redirect response here so it will work with just the backend
    response = RedirectResponse(reply_url)
    # add state as cookie for checking later
    response.set_cookie("orignial_state", state)

    return response


@app.get("/login_response")
async def login_response(
    settings: SettingsDependency,
    db_session: DbSessionDependency,
    crud: AuthTokenCrudDependency,
    spotify_client: SpotifyClientDependency,
    request: Request,
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> str:
    """Handle the Spotify login response"""
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

    token = await spotify_client.get_token(
        settings.base_url, settings.get_auth_header(), code
    )

    if token is None:
        _logger.error("get auth token failed")
        return "get_token_failed"

    await crud.replace_auth_token(db_session, token)

    return "login_successful"


@app.get("/auth_token")
async def auth_token(
    db_session: DbSessionDependency, crud: AuthTokenCrudDependency
) -> schemas.AuthToken | None:
    """Get the Spotify auth token"""
    return await crud.read_auth_token(db_session)


@app.get("/refresh_auth_token")
async def refresh_auth_token(
    settings: SettingsDependency,
    db_session: DbSessionDependency,
    crud: AuthTokenCrudDependency,
    spotify_client: SpotifyClientDependency,
) -> schemas.AuthToken | None:
    """Refresh the Spotify auth token"""

    old_token = await crud.read_auth_token(db_session)

    if old_token is None:
        _logger.error("no auth tokens present")
        return

    if old_token.expired():
        _logger.error("auth tokens expired")
        return

    new_token = await spotify_client.refresh_token(
        old_token, settings.get_auth_header()
    )
    if new_token is None:
        _logger.error("refresh auth token failed")
        return

    await crud.replace_auth_token(db_session, new_token)
    return new_token


@app.get("/update_artists_from_spotify")
async def update_artists_from_spotify(
    settings: SettingsDependency,
    db_session: DbSessionDependency,
    auth_token_crud: AuthTokenCrudDependency,
    artist_crud: ArtistCrudDependency,
    spotify_client: SpotifyClientDependency,
) -> list[schemas.Artist]:
    """Update artists from Spotify"""

    auth_token = await auth_token_crud.read_auth_token(db_session)
    if auth_token is None:
        _logger.error(
            "getting artists failed. No auth token. Please login first (visit /login)"
        )
        return []

    artists = await spotify_client.get_artists(settings.artists_to_track, auth_token)
    await artist_crud.update_artists(db_session, artists)
    return artists


@app.get("/artist/{artist_id}")
async def get_artist(
    db_session: DbSessionDependency,
    crud: ArtistCrudDependency,
    artist_id: str,
) -> schemas.Artist | None:
    """Get one artist by id"""
    return await crud.read_artist(db_session, artist_id)


@app.put("/artist/{artist_id}")
async def update_artist(
    db_session: DbSessionDependency,
    crud: ArtistCrudDependency,
    artist_id: str,
    artist: schemas.Artist,
) -> schemas.Artist | None:
    """Update one artist by id"""
    artist.id = artist_id  # do not allow changing the id
    return await crud.update_artist(db_session, artist, False, True)


@app.put("/artist/")
async def create_artist(
    db_session: DbSessionDependency,
    crud: ArtistCrudDependency,
    artist: schemas.Artist,
) -> schemas.Artist:
    """Create a new artist in the database"""
    return await crud.create_artist(db_session, artist)


@app.delete("/artist/{artist_id}")
async def delete_artist(
    db_session: DbSessionDependency,
    crud: ArtistCrudDependency,
    artist_id: str,
) -> None:
    """Delete one artist by id"""
    return await crud.delete_artist(db_session, artist_id)
