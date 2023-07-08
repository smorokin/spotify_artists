from fastapi.testclient import TestClient
from mocks import MockArtistCrud, MockAuthTokenCrud, MockSpotifyClient
from crud import ArtistCrud, AuthTokenCrud

from main import app

from schemas import AuthToken, Artist
from spotify import SpotifyClient


client = TestClient(
    app,
    base_url="http://localhost:8000",
)


app.dependency_overrides[AuthTokenCrud] = MockAuthTokenCrud


app.dependency_overrides[ArtistCrud] = MockArtistCrud


app.dependency_overrides[SpotifyClient] = MockSpotifyClient


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_login():
    response = client.get("/login", follow_redirects=False)

    assert response.status_code == 307
    assert "orignial_state" in response.cookies


def test_login_response_ok():
    MockAuthTokenCrud.reset()

    client.cookies = {"orignial_state": "orignial_state_test"}
    response = client.get(
        "/login_response",
        params={"state": "orignial_state_test", "code": "code_test"},
    )

    assert response.status_code == 200
    assert response.text == '"login_successful"'


def test_login_response_mismatched_state():
    MockAuthTokenCrud.reset()

    client.cookies = {"orignial_state": "orignial_state_test_wrong"}
    response = client.get(
        "/login_response",
        params={"state": "orignial_state_test", "code": "code_test"},
    )

    assert response.text == '"state_mismatch"'


def test_login_response_mismatched_error():
    MockAuthTokenCrud.reset()

    client.cookies = {"orignial_state": "orignial_state_test"}
    response = client.get(
        "/login_response",
        params={"state": "orignial_state_test", "error": "some_error"},
    )

    assert response.text == '"some_error"'


def test_auth_token():
    MockAuthTokenCrud.reset()

    response = client.get("/auth_token")

    assert response.status_code == 200
    assert response.json().get("access_token") is not None
    assert (
        AuthToken.validate(response.json()).refresh_token
        == MockAuthTokenCrud.auth_token.refresh_token
    )


def test_refresh_auth_token():
    MockAuthTokenCrud.reset()

    response = client.get("/refresh_auth_token")

    assert response.status_code == 200
    assert response.json().get("access_token") == "access_token_test_next"


def test_update_artists_from_spotify():
    response = client.get("/update_artists_from_spotify")

    assert response.status_code == 200
    json = response.json()
    assert len(json) == 2
    artists = [Artist.validate(j) for j in json]
    assert len(artists) == 2


def test_get_artist():
    response = client.get("/artist/a")

    assert response.status_code == 200
    json = response.json()
    artist = Artist.validate(json)
    assert artist.id == "a"


def test_update_artist():
    artist = MockArtistCrud.artists["a"]
    artist.followers.total = 1000_000
    data = artist.dict()

    response = client.put("/artist/a", json=data)

    assert response.status_code == 200
    json = response.json()
    response_artist = Artist.validate(json)
    assert response_artist.followers.total == artist.followers.total
