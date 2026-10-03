from pydantic import BaseModel


class Artifacts(BaseModel):
    paths: list[str]


class BaseJobInput(BaseModel):
    uid: str
    name: str
    stage: str
    script: list[str]
    variables: dict[str, str] | None = None
    artifacts: Artifacts | None = None
    load_artifacts: dict[str, str] | None = None
