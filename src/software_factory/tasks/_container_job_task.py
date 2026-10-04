from datetime import timedelta

from hatchet_sdk import Context

from ..artifacts import S3ArtifactStore
from ..hatchet_provider import hatchet
from ..job import ContainerJobInput, JobExecutor, Result
from ..job_runtime import DockerRuntime


@hatchet.task(
    name="container-job-task",
    input_validator=ContainerJobInput,
    execution_timeout=timedelta(hours=1),
)
def container_job_task(input_: ContainerJobInput, ctx: Context) -> Result:
    store = S3ArtifactStore.from_env()
    store.create_bucket_if_not_exists()
    with DockerRuntime(
        input_.image,
        "/root",
        ["sh"],
        command=["-c", "tail -f /dev/null"],
    ) as runtime:
        return JobExecutor(runtime, store).run(input_)
