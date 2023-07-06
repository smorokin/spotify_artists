from logging import getLogger
from typing import Sequence

from sqlalchemy import Select, select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSessionTransaction
from sqlalchemy.orm import selectinload

import models
import schemas
from db import DbSessionDependency


_logger = getLogger(__file__)


def _select_artists_with_relations() -> Select[tuple[models.Artist]]:
    return select(models.Artist).options(
        selectinload(models.Artist.genres),
        selectinload(models.Artist.external_urls),
        selectinload(models.Artist.followers),
        selectinload(models.Artist.images),
    )


async def replace_auth_token(
    db_session: DbSessionDependency, new_tokens: schemas.AuthToken
) -> None:
    # delete all old tokens
    async with db_session.begin():
        # delete all auth tokens (prevents storing multiples)
        delete_query = delete(models.AuthToken)
        await db_session.execute(delete_query)

        # create one new auth token (there should always only be one)
        create_query = insert(models.AuthToken).values(**(new_tokens.dict()))
        await db_session.execute(create_query)


async def read_auth_token(db_session: DbSessionDependency) -> schemas.AuthToken | None:
    async with db_session.begin():
        query = select(models.AuthToken)
        results = await db_session.execute(query)
        token = results.scalar_one_or_none()
        if token is None:
            return None

        return schemas.AuthToken.from_orm(token)


async def update_artist(
    db_session: DbSessionDependency,
    updated_artist: schemas.Artist,
    skip_modified_manually: bool = True,
    manual: bool = False,
) -> schemas.Artist:
    return (
        await update_artists(
            db_session, [updated_artist], skip_modified_manually, manual
        )
    )[0]


async def update_artists(
    db_session: DbSessionDependency,
    updated_artists: Sequence[schemas.Artist],
    skip_modified_manually: bool = True,
    manual: bool = False,
) -> Sequence[schemas.Artist]:
    async with db_session.begin() as transaction:
        # create genres beforhand (creating when creating the artists leads to errors of missing id values)
        genres = await _create_genres_if_missing(
            transaction,
            [genre.name for artist in updated_artists for genre in artist.genres],
        )

        artists_in_db_query = _select_artists_with_relations().where(
            models.Artist.id.in_([a.id for a in updated_artists])
        )

        artists_in_db = (await db_session.execute(artists_in_db_query)).scalars().all()
        artists_in_db_dict = {a.id: a for a in artists_in_db if a.id is not None}

        for updated_artist in updated_artists:
            artist_in_db = artists_in_db_dict.get(updated_artist.id)

            artist_dict = updated_artist.dict()
            artist_dict["genres"] = genres
            artist_dict["external_urls"] = models.ExternalUrls(
                **updated_artist.external_urls.dict(), id=updated_artist.id
            )
            artist_dict["followers"] = models.Followers(
                **updated_artist.followers.dict(), id=updated_artist.id
            )

            if artist_in_db is None:
                artist_dict["images"] = [
                    models.Image(**image.dict()) for image in updated_artist.images
                ]

                artist = models.Artist(**artist_dict)
                db_session.add(artist)
            else:
                if (
                    not manual
                    and skip_modified_manually
                    and artist_in_db.modified_manually
                ):
                    continue

                artist_dict["images"] = _update_images(
                    updated_artist.images, artist_in_db.images
                )

                artist_dict["modified_manually"] = manual

                for key in artist_dict.keys():
                    setattr(artist_in_db, key, artist_dict[key])
        artists_in_db = (await db_session.execute(artists_in_db_query)).scalars().all()
        return [schemas.Artist.from_orm(artist) for artist in artists_in_db]


async def _create_genres_if_missing(
    transaction: AsyncSessionTransaction, genre_names: Sequence[str]
) -> Sequence[models.Genre]:
    async with transaction.session.begin_nested():
        genres_in_db_query = select(models.Genre).where(
            models.Genre.name.in_(genre_names)
        )
        genres_in_db = (
            (await transaction.session.execute(genres_in_db_query)).scalars().all()
        )
        present_genre_names = [g.name for g in genres_in_db]
        missing_genre_names = [g for g in genre_names if g not in present_genre_names]

        if len(missing_genre_names) != 0:
            insert_genres_query = insert(models.Genre).values(
                [{"name": name} for name in missing_genre_names]
            )
            await transaction.session.execute(insert_genres_query)

        all_genres_query = select(models.Genre).where(
            models.Genre.name.in_(genre_names)
        )
        return (await transaction.session.execute(all_genres_query)).scalars().all()


def _update_images(
    new_images: list[schemas.Image], old_images: list[models.Image]
) -> list[models.Image]:
    old_urls = [image.url for image in old_images]
    new_urls = [image.url for image in new_images]
    missing_images = [image for image in new_images if image.url not in old_urls]
    old_images_to_keep = [image for image in old_images if image.url in new_urls]
    new_images_to_create = [models.Image(**image.dict()) for image in missing_images]

    old_images_to_keep.extend(new_images_to_create)
    return old_images_to_keep


async def read_artist(
    db_session: DbSessionDependency, artist_id: str
) -> schemas.Artist | None:
    async with db_session.begin():
        query = _select_artists_with_relations().where(models.Artist.id == artist_id)

        artist_db = (await db_session.execute(query)).scalar_one_or_none()
        if artist_db is None:
            return

    return schemas.Artist.from_orm(artist_db)


# create and delete artists are not required currently
