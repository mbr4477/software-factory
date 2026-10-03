from ._base_job_input import BaseJobInput


class RemoteSshJobInput(BaseJobInput):
    hostname: str
    user: str
    working_dir: str
    port: int = 22
