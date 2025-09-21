from pydantic import BaseModel


class Config(BaseModel, extra="ignore"):
    revoke_max_size: int = 100
