from pydantic import HttpUrl, parse_obj_as
import pytest
import pytest_asyncio
from sqlalchemy import select

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from db import Base
from crud import ArtistCrud, AuthTokenCrud
import schemas
import models


# use in memory sqlite db for testing
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def session_maker_fixture():
    """This fixture provides an independent db engine per test.
    It also creates the tables before the test and deletes them afterwards.
    This only works with pytest_asyncio, pytest_asyncio.fixture
    and pytest.mark.asyncio"""
    test_engine = create_async_engine(TEST_DATABASE_URL)
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_session_maker

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_replace_auth_token_when_none_exist(session_maker_fixture):
    first_token = schemas.AuthToken(
        access_token="access_token_test",
        refresh_token="refresh_token_test",
        expires_in=1234,
        scope="user-read-private user-read-email",
        token_type="token_type_test",
    )
    async with session_maker_fixture() as session:
        await AuthTokenCrud.replace_auth_token(session, first_token)

    async with session_maker_fixture() as session:
        tokens_in_db = (await session.execute(select(models.AuthToken))).scalars().all()

    assert len(tokens_in_db) == 1
    assert tokens_in_db[0].expires_in == first_token.expires_in


@pytest.mark.asyncio
async def test_replace_auth_token_when_one_exists(session_maker_fixture):
    first_token = schemas.AuthToken(
        access_token="access_token_test",
        refresh_token="refresh_token_test",
        expires_in=1234,
        scope="user-read-private user-read-email",
        token_type="token_type_test",
    )
    async with session_maker_fixture() as session:
        await AuthTokenCrud.replace_auth_token(session, first_token)

    second_token = schemas.AuthToken(
        access_token="access_token_test_2",
        refresh_token="refresh_token_test_2",
        expires_in=5678,
        scope="user-read-private user-read-email",
        token_type="token_type_test",
    )
    async with session_maker_fixture() as session:
        await AuthTokenCrud.replace_auth_token(session, second_token)

    async with session_maker_fixture() as session:
        tokens_in_db = (await session.execute(select(models.AuthToken))).scalars().all()

    assert len(tokens_in_db) == 1
    assert tokens_in_db[0].expires_in == second_token.expires_in


@pytest.mark.asyncio
async def test_update_artist(session_maker_fixture):
    _url = parse_obj_as(HttpUrl, "http://example.com/a")
    artist = schemas.Artist(
        id="a",
        type="artist",
        href=_url,
        name="test artist a",
        popularity=1,
        uri="",
        genres=[schemas.Genre(__root__="test genre")],
        external_urls=schemas.ExternalUrls(spotify=_url),
        followers=schemas.Followers(href=None, total=1),
        images=[schemas.Image(url=_url, height=10, width=20)],
    )

    async with session_maker_fixture() as session:
        returned_artist = await ArtistCrud.update_artist(session, artist)

    assert returned_artist == artist


@pytest.mark.asyncio
async def test_update_artist_skip_manually_modfied(session_maker_fixture):
    _url = parse_obj_as(HttpUrl, "http://example.com/a")
    artist = schemas.Artist(
        id="a",
        type="artist",
        href=_url,
        name="test artist a",
        popularity=1,
        uri="",
        genres=[schemas.Genre(__root__="test genre")],
        external_urls=schemas.ExternalUrls(spotify=_url),
        followers=schemas.Followers(href=None, total=1),
        images=[schemas.Image(url=_url, height=10, width=20)],
    )

    async with session_maker_fixture() as session:
        await ArtistCrud.update_artist(session, artist, manual=True)

    async with session_maker_fixture() as session:
        artist.popularity = 100
        returned_artist = await ArtistCrud.update_artist(session, artist, manual=False)

    assert returned_artist.popularity == 1


@pytest.mark.asyncio
async def test_read_artist(session_maker_fixture):
    _url = parse_obj_as(HttpUrl, "http://example.com/a")
    artist = schemas.Artist(
        id="a",
        type="artist",
        href=_url,
        name="test artist a",
        popularity=1,
        uri="",
        genres=[schemas.Genre(__root__="test genre")],
        external_urls=schemas.ExternalUrls(spotify=_url),
        followers=schemas.Followers(href=None, total=1),
        images=[schemas.Image(url=_url, height=10, width=20)],
    )

    async with session_maker_fixture() as session:
        await ArtistCrud.update_artist(session, artist, manual=True)

    async with session_maker_fixture() as session:
        artist_in_db = await ArtistCrud.read_artist(session, artist_id=artist.id)

    assert artist_in_db == artist
