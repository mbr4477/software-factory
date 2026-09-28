from .container_job import ContainerJob
from .pipeline_models import Result
from .remote_ssh_job import RemoteSshJob


class JobEngine:
    async def spawn_container_job(self, job: ContainerJob) -> Result: ...
    async def spawn_remote_ssh_job(self, job: RemoteSshJob) -> Result: ...
