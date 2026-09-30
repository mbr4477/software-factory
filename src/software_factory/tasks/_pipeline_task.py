from hatchet_sdk import DurableContext

from ..hatchet_provider import hatchet
from ..job import (
    ContainerJobInput,
    RemoteSshJobInput,
    Result,
)
from ..pipeline import (
    JobEngine,
    PipelineDef,
    PipelineExecutor,
)
from ._container_job_task import container_job_task
from ._remote_ssh_job_task import remote_ssh_job_task

PIPELINE_TASK_EVENT_KEY = "pipeline-task"


class HatchetJobEngine(JobEngine):
    async def spawn_container_job(self, job: ContainerJobInput) -> Result:
        return await container_job_task.aio_run(job)

    async def spawn_remote_ssh_job(self, job: RemoteSshJobInput) -> Result:
        return await remote_ssh_job_task.aio_run(job)


@hatchet.durable_task(
    name="pipeline-task",
    input_validator=PipelineDef,
    on_events=[PIPELINE_TASK_EVENT_KEY],
)
async def pipeline_task(input_: PipelineDef, ctx: DurableContext):
    await PipelineExecutor(HatchetJobEngine()).execute(ctx.task_run_id, input_)
