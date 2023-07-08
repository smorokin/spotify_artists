from datetime import datetime, timedelta, timezone
from typing import Any, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, HttpUrl
from pydantic.utils import GetterDict

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny


class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int  # seconds
    scope: str
    token_type: str
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True

    def expired(self) -> bool:
        return datetime.now(timezone.utc) > self.created + timedelta(
            seconds=self.expires_in
        )


class Followers(BaseModel):
    href: HttpUrl | None
    total: int

    class Config:
        orm_mode = True


class Image(BaseModel):
    url: HttpUrl
    height: int
    width: int

    class Config:
        orm_mode = True


class ExternalUrls(BaseModel):
    spotify: HttpUrl

    class Config:
        orm_mode = True


class Genre(BaseModel):
    __root__: str

    class Config:
        orm_mode = True

    # workaround of props and dict-override since an alias on __root__ is not working properly
    @property
    def name(self) -> str:
        return self.__root__

    @name.setter
    def set_name(self, val: str) -> None:
        self.__root__ = val

    def dict(self, *,
            include: Union["AbstractSetIntStr", "MappingIntStrAny"] | None = None,
            exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] | None = None,
            by_alias: bool = False,
            skip_defaults: bool | None = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False
        ) -> dict[str, Any]:
        d = super().dict(include=include, exclude=exclude, by_alias=by_alias, skip_defaults=skip_defaults, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults, exclude_none=exclude_none)
        d["name"] = self.__root__
        return d


class _UserGetter(GetterDict):
    def get(self, key: str, default: Any) -> Any:
        if key in {"genres"}:
            return [genre.name for genre in self._obj.genres]
        return super().get(key, default)


class Artist(BaseModel):
    id: str
    type: str
    href: HttpUrl
    name: str
    popularity: int
    uri: str
    genres: list[Genre]
    external_urls: ExternalUrls
    followers: Followers
    images: list[Image]

    class Config:
        orm_mode = True
        getter_dict = _UserGetter
