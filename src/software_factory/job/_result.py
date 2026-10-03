from pydantic import BaseModel


class Result(BaseModel):
    exit_code: int
    logs: list[str] | None = None
    artifacts: dict[str, str] | None = None
