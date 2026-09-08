from pydantic import BaseModel, ConfigDict, validate_call


class Vulnerability(BaseModel):
    id: str
    aliases: list[str] = []

    _source: str | None = None

    model_config = ConfigDict(extra="allow")

    @validate_call
    def model_post_init(self, context: dict[str, str] | None) -> None:
        if context is not None:
            self._source = context.get("source")
