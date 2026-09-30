from pydantic import BaseModel


class Artifacts(BaseModel):
    paths: list[str]


class BaseJobInput(BaseModel):
    uid: str
    name: str
    stage: str
    git_url: str
    script: list[str]
    branch_name: str = "main"
    variables: dict[str, str] = {}
    artifacts: Artifacts | None = None
    load_artifacts: dict[str, str] | None = None
