from base64 import b64encode
from os import environ
import secrets
import string
from random import randbytes
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from httpx import AsyncClient


app = FastAPI()


@app.get("/login")
async def login() -> RedirectResponse:
    client_id = environ.get("SPOTIFY_CLIENT_ID")
    state = ''.join(secrets.choice(string.ascii_uppercase + string.ascii_lowercase) for i in range(16))

    async with  AsyncClient() as client:
        reply = await client.get(
            "https://accounts.spotify.com/authorize",
            params={
                "client_id": client_id,
                "response_type": "code",
                "scope": "user-read-private user-read-email",
                "redirect_uri": "http://localhost:8000/login_response",
                "state": state
            },
            follow_redirects=True
        )
        # using a redirect response here so it will work with just the backend
        response = RedirectResponse(str(reply.url))
        # add state as cookie for later check
        response.set_cookie("orignial_state", state)
        
        return response

@app.get("/login_response")
async def login_response(request: Request, state: str, code: str | None, error: str | None = None) -> str:
    original_state = request.cookies.get("orignial_state")
    if original_state != state:
        return "state_mismatch"
    if error is not None:
        return error
    if code is None:
        return "no_code"
    
    client_id = environ.get("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_ID not set")
    client_secret = environ.get("SPOTIFY_CLIENT_SECRET", "SPOTIFY_CLIENT_SECRET not set")
    auth = b64encode(client_id.encode() + b':' + client_secret.encode()).decode("utf-8")
    
    async with  AsyncClient() as client:
        reply = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:8000/login_response"
            },
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            follow_redirects=True
        )
        reply_json = reply.json()
        access_token = reply_json.get("access_token")
        refresh_token = reply_json.get("refresh_token")
        if access_token is not None and refresh_token is not None:
            #TODO: store tokens!
            return "login_successful"
        
        return "get_token_failed"
        



    

