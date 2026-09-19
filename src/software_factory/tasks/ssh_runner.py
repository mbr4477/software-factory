import io
import os
import traceback

import fabric
from hatchet_sdk import Context

from software_factory.hatchet_provider import hatchet
from software_factory.tasks.runner import BaseRunnerInput, RunnerOutput

SSH_RUNNER_EVENT_KEY = "runner:ssh"


class SshRunnerInput(BaseRunnerInput):
    host: str
    user: str
    workdir: str
    shell: str | None = None
    port: int = 22


@hatchet.task(
    name="ssh-runner",
    on_events=[SSH_RUNNER_EVENT_KEY],
    input_validator=SshRunnerInput,
)
def ssh_runner(job: SshRunnerInput, ctx: Context) -> RunnerOutput:
    success = False
    clone_script = [
        f"rm -rf {job.workdir}/code",
        f"git clone -b {job.git_branch_name} {job.git_repo_url} {job.workdir}/code",
        f"cd {job.workdir}/code",
    ]
    script = clone_script + (job.before_script or []) + job.script

    logs = []
    with fabric.Connection(job.host, job.user, job.port, forward_agent=True) as conn:
        try:
            out_stream = io.StringIO()
            _ = conn.run(
                " && ".join(script),
                shell=job.shell or "/bin/bash",
                warn=True,
                out_stream=out_stream,
                err_stream=out_stream,
                env={k: v or os.environ.get(k, "") for k, v in job.env.items()},
                replace_env=True,
            )
            logs = out_stream.getvalue().split("\n")
            success = True
        except Exception as e:  # noqa: BLE001
            traceback.print_tb(e.__traceback__)
            print(str(e))
        finally:
            _ = conn.run(f"rm -rf {job.workdir}/code", warn=True)
    return RunnerOutput(success=success, logs=logs)
