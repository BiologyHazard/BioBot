from pydantic import BaseModel


class Config(BaseModel):
    whitelist_groups: list[int]
