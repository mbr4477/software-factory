from datetime import timedelta

from hatchet_sdk import DurableContext

from ..hatchet_provider import hatchet
from ..job import (
    ContainerJobInput,
    RemoteSshJobInput,
    Result,
)
from ..pipeline import (
    JobDispatcher,
    PipelineDef,
    PipelineExecutor,
)
from ._container_job_task import container_job_task
from ._remote_ssh_job_task import remote_ssh_job_task


class HatchetJobEngine(JobDispatcher):
    async def dispatch_container_job(self, job: ContainerJobInput) -> Result:
        return await container_job_task.aio_run(job)

    async def dispatch_remote_ssh_job(self, job: RemoteSshJobInput) -> Result:
        return await remote_ssh_job_task.aio_run(job)


@hatchet.durable_task(
    name="pipeline-task",
    input_validator=PipelineDef,
    execution_timeout=timedelta(hours=1),
)
async def pipeline_task(input_: PipelineDef, ctx: DurableContext):
    await PipelineExecutor(HatchetJobEngine()).execute(ctx.task_run_id, input_)
