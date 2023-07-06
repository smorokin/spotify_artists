from __future__ import annotations

from typing import Any
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from db import Base

_STR_SIZE_HUGE = 512
_STR_SIZE_LONG = 128
_STR_SIZE_SHORT = 64


association_table = Table(
    "artist_genre_association_table",
    Base.metadata,
    Column("left_id", ForeignKey("artist.id"), primary_key=True),
    Column("right_id", ForeignKey("genre.id"), primary_key=True),
)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(String(_STR_SIZE_HUGE), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(_STR_SIZE_HUGE), nullable=False)
    expires_in: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    scope: Mapped[str] = mapped_column(String(_STR_SIZE_SHORT), nullable=False)
    token_type: Mapped[str] = mapped_column(String(_STR_SIZE_SHORT), nullable=False)

    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id}


class Genre(Base):
    __tablename__ = "genre"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)
    artists: Mapped[list[Artist]] = relationship(
        secondary=association_table, back_populates="genres"
    )

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name}


class Image(Base):
    __tablename__ = "image"
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    artist_id: Mapped[str] = mapped_column(ForeignKey("artist.id"))
    artist: Mapped[Artist] = relationship(back_populates="images")

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id}


class ExternalUrls(Base):
    __tablename__ = "external_urls"
    id: Mapped[str] = mapped_column(primary_key=True)
    spotify: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)

    # one to one
    artist_id: Mapped[str] = mapped_column(ForeignKey("artist.id"))
    artist: Mapped[Artist] = relationship(back_populates="external_urls")

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id}


class Followers(Base):
    __tablename__ = "followers"
    id: Mapped[str] = mapped_column(primary_key=True)
    href: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # one to one
    artist_id: Mapped[str] = mapped_column(ForeignKey("artist.id"))
    artist: Mapped[Artist] = relationship(back_populates="followers")

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id}


class Artist(Base):
    __tablename__ = "artist"
    id: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), primary_key=True)
    type: Mapped[str] = mapped_column(
        String(_STR_SIZE_SHORT), default="artist", nullable=False
    )
    href: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)
    name: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)
    popularity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uri: Mapped[str] = mapped_column(String(_STR_SIZE_LONG), nullable=False)

    modified_manually: Mapped[bool] = mapped_column(nullable=False, default=False)

    genres: Mapped[list[Genre]] = relationship(
        secondary=association_table, back_populates="artists"
    )

    external_urls: Mapped[ExternalUrls] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )

    followers: Mapped[Followers] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )

    images: Mapped[list[Image]] = relationship(
        back_populates="artist", cascade="all, delete-orphan"
    )

    def repr_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name}
