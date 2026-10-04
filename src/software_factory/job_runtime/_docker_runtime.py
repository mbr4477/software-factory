import io
import os
import tarfile
from typing import Self

from docker.errors import ImageNotFound, NotFound
from docker.types import Mount

import docker

from ._job_runtime import ExecResult, JobRuntime


class InvalidRemotePath(Exception): ...


class DockerRuntime(JobRuntime):
    def __init__(
        self,
        image: str,
        working_dir: str,
        entrypoint: list[str] | None = None,
        command: list[str] | None = None,
    ):
        self._working_dir = working_dir
        self._entrypoint = entrypoint or ["/bin/bash"]

        self._client = docker.client.from_env()
        try:
            self._client.images.get(image)
        except ImageNotFound:
            self._client.images.pull(image)

        env = {"GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=no"}
        mounts = []
        if "SSH_AUTH_SOCK" in os.environ:
            mounts.append(
                Mount(
                    "/ssh-agent",
                    os.environ.get("SSH_AUTH_SOCK"),
                    type="bind",
                )
            )
            env["SSH_AUTH_SOCK"] = "/ssh-agent"

        self._container = self._client.containers.create(
            image,
            command,
            entrypoint=entrypoint,
            working_dir=working_dir,
            mounts=mounts,
            environment=env,
            detach=True,
        )
        self._container.start()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb):
        self.destroy()

    def _is_valid_path(self, path: str) -> bool:
        return "./" not in path

    def get_file(self, remote_source: str, local_dest: str):
        if not self._is_valid_path(remote_source):
            raise InvalidRemotePath()

        try:
            bits, _ = self._container.get_archive(
                f"{self._working_dir}/{remote_source}"
            )
        except NotFound as e:
            raise FileNotFoundError(e.explanation)

        stream = io.BytesIO(b"".join(bits))
        with tarfile.open(fileobj=stream, mode="r") as tar:
            member = tar.getmembers()[0]
            data = tar.extractfile(member)
            if data is not None:
                with data, open(local_dest, "wb") as local_file:
                    local_file.write(data.read())

    def put_file(self, local_source: str, remote_dest: str):
        if not self._is_valid_path(remote_dest):
            raise InvalidRemotePath()

        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            tar.add(local_source, arcname=f"/{self._working_dir}/{remote_dest}")
        stream.seek(0)
        self._container.put_archive("/", data=stream)

    def is_dir(self, remote_path: str) -> bool:
        if not self._is_valid_path(remote_path):
            raise InvalidRemotePath()

        result = self._container.exec_run(
            ["[", "-d", f"{self._working_dir}/{remote_path}", "]"]
        )
        return result.exit_code == 0

    def list_tree(self, remote_dir: str) -> list[str]:
        if not self._is_valid_path(remote_dir):
            raise InvalidRemotePath()

        result = self._container.exec_run(
            ["find", f"{self._working_dir}/{remote_dir}", "-type", "f"]
        )

        if result.exit_code != 0:
            raise RuntimeError()

        stdout = (
            result.output.decode()
            if isinstance(result.output, bytes)
            else b"".join(result.output).decode()
        )
        paths = [
            p.removeprefix(f"{self._working_dir}/")
            for p in stdout.strip().split("\n")
            if p
        ]
        return paths

    def exec(self, cmd: str, env: dict[str, str] | None = None) -> ExecResult:
        result = self._container.exec_run(
            [*self._entrypoint, "-c", cmd], environment=env
        )
        stdout = (
            result.output.decode()
            if isinstance(result.output, bytes)
            else b"".join(result.output).decode()
        ).strip()
        return ExecResult(result.exit_code or 0, stdout)

    def destroy(self):
        self._container.stop(timeout=0)
        self._container.remove()
