from typing import Literal

from .base_job import BaseJob


class ContainerJob(BaseJob):
    type: Literal["container"]
    image: str
    entrypoint: list[str] | None = None
