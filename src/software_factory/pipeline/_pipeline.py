from pydantic import BaseModel, model_validator

from ..job import ContainerJob, RemoteSshJob

JSONValue = dict[str, "JSONValue"] | list["JSONValue"] | str | int | float | bool | None


class Pipeline(BaseModel):
    stages: list[str]
    max_backtracks: int
    jobs: dict[str, ContainerJob | RemoteSshJob] = {}

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


def pipeline_from_dict(content: dict[str, JSONValue]) -> Pipeline:
    return Pipeline.model_validate(content)
