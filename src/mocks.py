from db import DbSessionDependency
from schemas import Artist, AuthToken, ExternalUrls, Followers, Genre, Image


from pydantic import AnyHttpUrl, HttpUrl, parse_obj_as


from typing import Sequence


class MockArtistCrud:
    _url = parse_obj_as(HttpUrl, "http://example.com/a")
    artists = {
        "a": Artist(
            id="a",
            type="artist",
            href=_url,
            name="test artist a",
            popularity=1,
            uri="",
            genres=[Genre(__root__="test genre")],
            external_urls=ExternalUrls(spotify=_url),
            followers=Followers(href=None, total=1),
            images=[Image(url=_url, height=10, width=20)],
        ),
        "b": Artist(
            id="b",
            type="artist",
            href=_url,
            name="test artist b",
            popularity=10,
            uri="",
            genres=[Genre(__root__="test genre")],
            external_urls=ExternalUrls(spotify=_url),
            followers=Followers(href=None, total=1),
            images=[Image(url=_url, height=10, width=20)],
        ),
    }

    manual: set[str] = set()

    @classmethod
    async def update_artist(
        cls,
        db_session: DbSessionDependency,
        updated_artist: Artist,
        skip_modified_manually: bool = True,
        manual: bool = False,
    ) -> Artist:
        return (
            await MockArtistCrud.update_artists(
                db_session, [updated_artist], skip_modified_manually, manual
            )
        )[0]

    @classmethod
    async def update_artists(
        cls,
        db_session: DbSessionDependency,
        updated_artists: Sequence[Artist],
        skip_modified_manually: bool = True,
        manual: bool = False,
    ) -> Sequence[Artist]:
        if skip_modified_manually:
            updated_artists = [
                artist for artist in updated_artists if artist.id not in cls.manual
            ]
        if manual:
            cls.manual.update([artist.id for artist in updated_artists])

        for artist in updated_artists:
            cls.artists[artist.id] = artist

        return updated_artists

    @classmethod
    async def read_artist(
        cls, db_session: DbSessionDependency, artist_id: str
    ) -> Artist | None:
        return cls.artists.get(artist_id)


class MockAuthTokenCrud:
    _auth_token = AuthToken(
        access_token="access_token_test_initial",
        refresh_token="refresh_token_test_initial",
        expires_in=3599,
        scope="user-read-private user-read-email",
        token_type="token_type_test",
    )

    auth_token = _auth_token.copy(deep=True)

    @classmethod
    async def replace_auth_token(
        cls, db_session: DbSessionDependency, new_tokens: AuthToken
    ) -> None:
        cls.auth_token = new_tokens

    @classmethod
    async def read_auth_token(
        cls,
        db_session: DbSessionDependency,
    ) -> AuthToken | None:
        return cls.auth_token

    @classmethod
    def reset(cls) -> None:
        cls.auth_token = cls._auth_token.copy(deep=True)


class MockSpotifyClient:
    login_token = AuthToken(
        access_token="access_token_test",
        refresh_token="refresh_token_test",
        expires_in=3601,
        scope="user-read-private user-read-email",
        token_type="token_type_test",
    )

    @classmethod
    async def login(
        cls, client_id: str, base_url: AnyHttpUrl, state: str
    ) -> AnyHttpUrl:
        print()
        return parse_obj_as(AnyHttpUrl, "http://example.com/spotify_sim")

    @classmethod
    async def get_token(
        cls, base_url: AnyHttpUrl, auth_header: str, code: str
    ) -> AuthToken | None:
        return MockSpotifyClient.login_token

    @classmethod
    async def refresh_token(
        cls, old_token: AuthToken, auth_header: str
    ) -> AuthToken | None:
        return AuthToken(
            access_token="access_token_test_next",
            refresh_token=old_token.refresh_token,
            expires_in=3602,
            scope="user-read-private user-read-email",
            token_type="token_type_test",
        )

    @classmethod
    async def get_artists(
        cls, artist_ids: list[str], auth_token: AuthToken
    ) -> list[Artist]:
        return list(MockArtistCrud.artists.values())
