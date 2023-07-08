# Spotify Artists

## Description
A sample project using `fastapi`, `celery`, `sqlalchemy` in combination with `postgresql`, `httpx` and `pytest`.

## Development
The package manager `pdm` is used to manage dependencies. For installation instructions see [its website](https://pdm.fming.dev/).

A `devcontainer` is included based on the provided `docker-compose.yml`. It also includes both a `redis` and a `postgresql` service.

Alternatively an equivalent environment can be used.

## Usage

An environment file `.env` must be placed inside the root directory of the project to run the application. Its content should look like this:

```bash
BASE_URL=http://localhost:8000

POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_HOST=postgres
POSTGRES_PASSWORD=postgres

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

SPOTIFY_CLIENT_ID=<YOUR_CLIENT_ID>
SPOTIFY_CLIENT_SECRET=<YOUR_CLIENT_SECRET>

ARTISTS_TO_TRACK='["57ylwQTnFnIhJh4nu4rxCs","3o2dn2O0FCVsWDFSh8qxgG"]'
```

Start the service with `docker compose up` from  the project root directory.
Visit `http://localhost:8000/login` to initiate the login to Spotify. You will be asked to enter your Spotify credentials.

You can then visit `http://localhost:8000/docs` to learn more about the avialable rest endpoints.
