import io
import os
import traceback
from datetime import timedelta

import fabric
from hatchet_sdk import Context

from software_factory.hatchet_provider import hatchet
from software_factory.pipeline import RemoteSshJob, Result

REMOTE_SSH_JOB_EVENT_KEY = "remote-ssh-job-task"


class RemoteSshJobTask:
    def run(self, job: RemoteSshJob) -> Result:
        exit_code = -1
        clone_script = [
            f"rm -rf {job.working_dir}/code",
            f"git clone -b {job.branch_name} {job.git_url} {job.working_dir}/code",
            f"cd {job.working_dir}/code",
        ]
        script = clone_script + job.script

        logs = []
        with fabric.Connection(
            job.hostname, job.user, job.port, forward_agent=True
        ) as conn:
            try:
                out_stream = io.StringIO()
                result = conn.run(
                    " && ".join(script),
                    warn=True,
                    out_stream=out_stream,
                    err_stream=out_stream,
                    env={
                        k: v or os.environ.get(k, "") for k, v in job.variables.items()
                    },
                    replace_env=True,
                )
                logs = out_stream.getvalue().split("\n")
                exit_code = result.exited
            except Exception as e:  # noqa: BLE001
                traceback.print_tb(e.__traceback__)
                print(str(e))
            finally:
                _ = conn.run(f"rm -rf {job.working_dir}/code", warn=True)
        return Result(exit_code=exit_code, logs=logs)


@hatchet.task(
    name="remote-ssh-job-task",
    on_events=[REMOTE_SSH_JOB_EVENT_KEY],
    input_validator=RemoteSshJob,
    execution_timeout=timedelta(hours=1),
)
def remote_ssh_job_task(input_: RemoteSshJob, ctx: Context) -> Result:
    return RemoteSshJobTask().run(input_)
