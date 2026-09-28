from hatchet_sdk import DurableContext

from software_factory.hatchet_provider import hatchet
from software_factory.pipeline import (
    ContainerJob,
    JobEngine,
    Pipeline,
    PipelineExecutor,
    RemoteSshJob,
    Result,
)
from software_factory.tasks import container_job_task, remote_ssh_job_task

PIPELINE_TASK_EVENT_KEY = "pipeline-task"


class HatchetJobEngine(JobEngine):
    async def spawn_container_job(self, job: ContainerJob) -> Result:
        return await container_job_task.aio_run(job)

    async def spawn_remote_ssh_job(self, job: RemoteSshJob) -> Result:
        return await remote_ssh_job_task.aio_run(job)


@hatchet.durable_task(
    name="pipeline-task", input_validator=Pipeline, on_events=[PIPELINE_TASK_EVENT_KEY]
)
async def pipeline_task(input_: Pipeline, ctx: DurableContext):
    await PipelineExecutor(input_, HatchetJobEngine()).execute()
