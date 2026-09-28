from typing import Literal

from .base_job import BaseJob


class RemoteSshJob(BaseJob):
    type: Literal["remote_ssh"]
    hostname: str
    user: str
    working_dir: str
    port: int = 22
