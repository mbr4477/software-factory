import os
import stat
import tempfile
from datetime import timedelta

from docker.types import Mount
from hatchet_sdk import Context

import docker
from software_factory.hatchet_provider import hatchet
from software_factory.pipeline import ContainerJob, Result

CONTAINER_JOB_TASK_EVENT_KEY = "container-job-task"


class ContainerJobTask:
    def run(self, job: ContainerJob) -> Result:
        client = docker.from_env()
        status_code = -1
        with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as tmpdir:
            clone_script = [
                "#!/bin/sh",
                "set -e",
                'export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"',
                f"git clone -b {job.branch_name} {job.git_url} /code",
                "cd /code",
            ]
            script = clone_script + job.script
            script_path = os.path.join(tmpdir, "script.sh")
            with open(script_path, "w") as script_file:
                script_file.write("\n".join(script))
                script_file.write("\n")
            os.chmod(script_path, stat.S_IRWXU | stat.S_IRWXO | stat.S_IRWXG)

            ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK", None)
            assert ssh_auth_sock is not None, "SSH_AUTH_SOCK not set"

            mounts = [
                Mount("/tmp/script.sh", script_path, type="bind", read_only=True),
                Mount(
                    "/ssh-agent",
                    ssh_auth_sock,
                    type="bind",
                ),
            ]

            env = {"SSH_AUTH_SOCK": "/ssh-agent"}
            env.update(
                {k: v or os.environ.get(k, "") for k, v in job.variables.items()}
            )

            container = client.containers.run(
                job.image,
                command=["/tmp/script.sh"],
                stdout=True,
                stderr=True,
                entrypoint=job.entrypoint,
                mounts=mounts,
                environment=env,
                detach=True,
            )
            result = container.wait()
            status_code = result["StatusCode"]
            logs = container.logs().decode().split("\n")
            container.remove()

        return Result(exit_code=status_code, logs=logs)


@hatchet.task(
    name="container-job-task",
    on_events=[CONTAINER_JOB_TASK_EVENT_KEY],
    input_validator=ContainerJob,
    execution_timeout=timedelta(hours=1),
)
def container_job_task(input_: ContainerJob, ctx: Context) -> Result:
    return ContainerJobTask().run(input_)
