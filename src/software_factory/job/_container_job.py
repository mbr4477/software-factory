import io
import os
import pathlib
import shutil
import stat
import tarfile
import tempfile

from docker.types import Mount

import docker

from ..artifacts import ArtifactStore
from ._base_job_input import BaseJobInput
from ._result import Result


class ContainerJobInput(BaseJobInput):
    image: str
    entrypoint: list[str] | None = None


class ContainerJob:
    def __init__(self, artifact_store: ArtifactStore):
        self._artifact_store = artifact_store

    def run(self, job: ContainerJobInput) -> Result:
        client = docker.from_env()
        status_code = -1
        with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as tmpdir:
            clone_script = [
                'export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"',
                f"git clone -b {job.branch_name} {job.git_url} /code",
            ]
            script = ["set -e", "cd /code"] + job.script
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

            container = client.containers.create(
                job.image,
                command=["-f", "/dev/null"],
                entrypoint="tail",
                mounts=mounts,
                environment=env,
                detach=True,
            )
            container.start()
            clone_result = container.exec_run(
                ["/bin/sh", "-c", " && ".join(clone_script)]
            )

            assert (
                clone_result.exit_code == 0
            ), f"Failed to clone:\n\n{clone_result.output.decode()}"

            if job.load_artifacts:
                # We need to load existing artifacts
                for object_key, path in job.load_artifacts.items():
                    basename = os.path.basename(path)
                    local_dirname = os.path.join(tmpdir, "artifacts")
                    os.makedirs(local_dirname, exist_ok=True)
                    local_path = os.path.join(local_dirname, basename)
                    self._artifact_store.get_object(object_key, local_path)
                    stream = io.BytesIO()
                    with tarfile.open(fileobj=stream, mode="w") as tar:
                        tar.add(local_path, arcname=f"/code/{path}")
                    stream.seek(0)
                    container.put_archive("/", data=stream)

            result = container.exec_run(
                (job.entrypoint or ["/bin/bash"]) + ["/tmp/script.sh"]
            )
            container.stop(timeout=0)
            status_code = result.exit_code
            # logs = container.logs().decode().split("\n")
            logs = result.output.decode().split("\n")

            out_artifacts = {}
            if job.artifacts:
                for path in job.artifacts.paths:
                    local_dir = os.path.join(tmpdir, "archive")
                    shutil.rmtree(local_dir, ignore_errors=True)
                    os.makedirs(local_dir, exist_ok=True)
                    bits, _ = container.get_archive(f"/code/{path}")
                    stream = io.BytesIO(b"".join(bits))
                    with tarfile.open(fileobj=stream, mode="r") as tar:
                        # Extract all the files in the archive
                        tar.extractall(local_dir)
                    for file in pathlib.Path(local_dir).rglob("*"):
                        if file.is_file():
                            rel_path = file.relative_to(local_dir)
                            key = f"{job.uid}/{rel_path}"
                            self._artifact_store.put_object(key, str(file))
                            out_artifacts[key] = str(rel_path)

            container.remove()

        return Result(exit_code=status_code, logs=logs, artifacts=out_artifacts)
