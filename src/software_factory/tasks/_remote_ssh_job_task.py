from datetime import timedelta

from hatchet_sdk import Context

from ..hatchet_provider import hatchet
from ..job import RemoteSshJob, RemoteSshJobInput, Result

REMOTE_SSH_JOB_EVENT_KEY = "remote-ssh-job-task"


@hatchet.task(
    name="remote-ssh-job-task",
    on_events=[REMOTE_SSH_JOB_EVENT_KEY],
    input_validator=RemoteSshJobInput,
    execution_timeout=timedelta(hours=1),
)
def remote_ssh_job_task(input_: RemoteSshJobInput, ctx: Context) -> Result:
    return RemoteSshJob().run(input_)
