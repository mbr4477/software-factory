import os
import tempfile

import docker.errors
from docker.types import Mount
from hatchet_sdk import Context

import docker
from software_factory.hatchet_provider import hatchet
from software_factory.tasks.runner import BaseRunnerInput, RunnerOutput

CONTAINER_RUNNER_EVENT_KEY = "runner:container"


class ContainerRunnerInput(BaseRunnerInput):
    image: str
    entrypoint: list[str] | None = None
    user: str | None = None


@hatchet.task(
    name="container-runner",
    on_events=[CONTAINER_RUNNER_EVENT_KEY],
    input_validator=ContainerRunnerInput,
)
def container_runner(job: ContainerRunnerInput, ctx: Context) -> RunnerOutput:
    client = docker.from_env()
    success = False
    with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as tmpdir:
        try:
            clone_script = [
                "#!/bin/sh",
                f"git clone -b {job.git_branch_name} {job.git_repo_url} /code",
                "cd /code",
            ]
            script = clone_script + (job.before_script or []) + job.script
            script_path = os.path.join(tmpdir, "script.sh")
            with open(script_path, "w") as script_file:
                script_file.write("\n".join(script))
                script_file.write("\n")

            mounts = [
                Mount("/tmp/script.sh", script_path, type="bind", read_only=True),
                Mount(
                    "/root/.ssh",
                    os.path.join(os.path.expanduser("~"), ".ssh"),
                    type="bind",
                    read_only=True,
                ),
            ]
            logs = (
                client.containers.run(
                    job.image,
                    command=["/tmp/script.sh"],
                    stdout=True,
                    stderr=True,
                    entrypoint=job.entrypoint,
                    auto_remove=True,
                    mounts=mounts,
                    environment={
                        k: v or os.environ.get(k, "") for k, v in job.env.items()
                    },
                    user=job.user,
                )
                .decode()
                .split("\n")
            )
            success = True
        except docker.errors.ContainerError as e:
            logs = e.container.logs().decode().split("\n")
    return RunnerOutput(success=success, logs=logs)
