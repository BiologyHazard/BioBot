from nonebot import get_plugin_config
from pydantic import BaseModel, Field, model_validator


class Config(BaseModel):
    """Configuration for read-only GitHub queries."""

    github_query_github_token: str | None = None
    github_query_default_limit: int = Field(default=10, ge=1, le=100)
    github_query_max_limit: int = Field(default=30, ge=1, le=100)
    github_query_max_pages: int = Field(default=10, ge=1, le=100)
    github_query_request_timeout: float = Field(default=15, ge=1)

    @model_validator(mode="after")
    def validate_limits(self) -> "Config":
        if self.github_query_default_limit > self.github_query_max_limit:
            raise ValueError(
                "github_query_default_limit must not exceed github_query_max_limit"
            )
        return self


plugin_config = get_plugin_config(Config)
