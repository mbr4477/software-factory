from typing import Literal

from pydantic import BaseModel, model_validator

JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None


class ArtifactsDef(BaseModel):
    paths: list[str]


class BaseJobDef(BaseModel):
    name: str
    stage: str
    script: list[str]
    on_fail: str | None = None
    variables: dict[str, str] = {}
    artifacts: ArtifactsDef | None = None


class ContainerJobDef(BaseJobDef):
    type: Literal["container"]
    image: str
    entrypoint: list[str] | None = None


class RemoteSshJobDef(BaseJobDef):
    type: Literal["remote_ssh"]
    hostname: str
    user: str
    working_dir: str
    port: int = 22


class PipelineDef(BaseModel):
    stages: list[str]
    max_backtracks: int
    jobs: dict[str, ContainerJobDef | RemoteSshJobDef] = {}

    @model_validator(mode="before")
    @classmethod
    def gather_jobs(cls, data: dict[str, JSONValue]) -> dict[str, JSONValue]:
        stages = data.get("stages", [])
        jobs = {
            k: {"name": k, **v}
            for k, v in data.items()
            if k not in ("stages", "max_backtracks", "jobs")
        }
        jobs.update(data.get("jobs", {}))
        return {
            "stages": stages,
            "max_backtracks": data["max_backtracks"],
            "jobs": jobs,
        }


def pipeline_def_from_dict(content: dict[str, JSONValue]) -> PipelineDef:
    return PipelineDef.model_validate(content)
