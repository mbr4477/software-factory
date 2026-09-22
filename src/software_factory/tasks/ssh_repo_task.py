import io
import os
import traceback

import fabric
from hatchet_sdk import Context

from software_factory.hatchet_provider import hatchet
from software_factory.tasks.repo_task import BaseRepoTaskInput, RepoTaskOutput

SSH_REPO_TASK_EVENT_KEY = "ssh-repo-task"


class SshRepoTaskInput(BaseRepoTaskInput):
    host: str
    user: str
    workdir: str
    shell: str | None = None
    port: int = 22


class SshRepoTask:
    def run(self, job: SshRepoTaskInput) -> RepoTaskOutput:
        success = False
        clone_script = [
            f"rm -rf {job.workdir}/code",
            f"git clone -b {job.git_branch_name} {job.git_repo_url} {job.workdir}/code",
            f"cd {job.workdir}/code",
        ]
        script = clone_script + (job.before_script or []) + job.script

        logs = []
        with fabric.Connection(
            job.host, job.user, job.port, forward_agent=True
        ) as conn:
            try:
                out_stream = io.StringIO()
                result = conn.run(
                    " && ".join(script),
                    shell=job.shell or "/bin/bash",
                    warn=True,
                    out_stream=out_stream,
                    err_stream=out_stream,
                    env={k: v or os.environ.get(k, "") for k, v in job.env.items()},
                    replace_env=True,
                )
                logs = out_stream.getvalue().split("\n")
                success = result.exited == 0
            except Exception as e:  # noqa: BLE001
                traceback.print_tb(e.__traceback__)
                print(str(e))
            finally:
                _ = conn.run(f"rm -rf {job.workdir}/code", warn=True)
        return RepoTaskOutput(success=success, logs=[line for line in logs if line])


@hatchet.task(
    name="ssh-runner",
    on_events=[SSH_REPO_TASK_EVENT_KEY],
    input_validator=SshRepoTaskInput,
)
def ssh_repo_task(input_: SshRepoTaskInput, ctx: Context) -> RepoTaskOutput:
    return SshRepoTask().run(input_)
