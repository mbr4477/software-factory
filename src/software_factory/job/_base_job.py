from pydantic import BaseModel


class Artifacts(BaseModel):
    paths: list[str]


class BaseJob(BaseModel):
    name: str
    stage: str
    git_url: str
    script: list[str]
    branch_name: str = "main"
    on_fail: str | None = None
    variables: dict[str, str] = {}
    artifacts: Artifacts | None = None
