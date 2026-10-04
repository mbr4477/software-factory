from datetime import timedelta

from hatchet_sdk import Context

from ..artifacts import S3ArtifactStore
from ..hatchet_provider import hatchet
from ..job import JobExecutor, RemoteSshJobInput, Result
from ..job_runtime import RemoteSshRuntime


@hatchet.task(
    name="remote-ssh-job-task",
    input_validator=RemoteSshJobInput,
    execution_timeout=timedelta(hours=1),
)
def remote_ssh_job_task(input_: RemoteSshJobInput, ctx: Context) -> Result:
    store = S3ArtifactStore.from_env()
    store.create_bucket_if_not_exists()
    with RemoteSshRuntime(
        input_.hostname, input_.user, input_.working_dir, input_.port
    ) as runtime:
        return JobExecutor(runtime, store).run(input_)
