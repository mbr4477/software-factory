import os
import stat
import tempfile

from docker.types import Mount
from hatchet_sdk import Context
from pydantic import BaseModel

import docker
from software_factory.hatchet_provider import hatchet
from software_factory.tasks.repo_task import BaseRepoTaskInput, RepoTaskOutput

CONTAINER_REPO_TASK_EVENT_KEY = "container-repo-task"


class Volume(BaseModel):
    name: str
    mount_point: str


class ContainerRepoTaskInput(BaseRepoTaskInput):
    image: str
    entrypoint: list[str] | None = None
    user: str | None = None
    volumes: list[Volume] | None = None


class ContainerRepoTask:
    def run(self, job: ContainerRepoTaskInput) -> RepoTaskOutput:
        client = docker.from_env()
        success = False
        with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as tmpdir:
            clone_script = [
                "#!/bin/sh",
                "set -e",
                'export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"',
                f"git clone -b {job.git_branch_name} {job.git_repo_url} /code",
                "cd /code",
            ]
            script = clone_script + (job.before_script or []) + job.script
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
            if job.volumes:
                for v in job.volumes:
                    mounts.append(Mount(v.mount_point, v.name, type="volume"))

            env = {"SSH_AUTH_SOCK": "/ssh-agent"}
            env.update({k: v or os.environ.get(k, "") for k, v in job.env.items()})

            container = client.containers.run(
                job.image,
                command=["/tmp/script.sh"],
                stdout=True,
                stderr=True,
                entrypoint=job.entrypoint,
                mounts=mounts,
                environment=env,
                user=job.user,
                detach=True,
            )
            result = container.wait()
            success = result["StatusCode"] == 0
            logs = container.logs().decode().split("\n")
            container.remove()
        return RepoTaskOutput(success=success, logs=[line for line in logs if line])


@hatchet.task(
    name="container-repo-task",
    on_events=[CONTAINER_REPO_TASK_EVENT_KEY],
    input_validator=ContainerRepoTaskInput,
)
def container_repo_task(input_: ContainerRepoTaskInput, ctx: Context) -> RepoTaskOutput:
    return ContainerRepoTask().run(input_)
