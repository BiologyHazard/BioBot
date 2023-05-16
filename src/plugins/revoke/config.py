from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    revoke_max_size: int = 100
