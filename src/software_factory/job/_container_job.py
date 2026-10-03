from ._base_job_input import BaseJobInput


class ContainerJobInput(BaseJobInput):
    image: str
    entrypoint: list[str] | None = None
