import io
import os
from typing import Self

import fabric

from ._job_runtime import ExecResult, JobRuntime


class InvalidRemotePath(Exception): ...


class RemoteSshRuntime(JobRuntime):
    def __init__(self, hostname: str, user: str, working_dir: str, port: int = 22):
        self._working_dir = working_dir
        self._conn = fabric.Connection(hostname, user, port, forward_agent=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb):
        self.destroy()

    def _is_valid_path(self, path: str) -> bool:
        return "./" not in path

    def get_file(self, remote_source: str, local_dest: str):
        if not self._is_valid_path(remote_source):
            raise InvalidRemotePath()
        _ = self._conn.get(f"{self._working_dir}/{remote_source}", local=local_dest)

    def put_file(self, local_source: str, remote_dest: str):
        if not self._is_valid_path(remote_dest):
            raise InvalidRemotePath()

        remote_path = f"{self._working_dir}/{remote_dest}"
        remote_dir = os.path.dirname(remote_path)
        _ = self._conn.run(f"mkdir -p {remote_dir}")
        _ = self._conn.put(local_source, remote_path)

    def is_dir(self, remote_path: str) -> bool:
        if not self._is_valid_path(remote_path):
            raise InvalidRemotePath()

        result = self._conn.run(f"[ -d {self._working_dir}/{remote_path} ]", warn=True)
        return result.exited == 0

    def list_tree(self, remote_dir: str) -> list[str]:
        if not self._is_valid_path(remote_dir):
            raise InvalidRemotePath()

        stream = io.StringIO()
        result = self._conn.run(
            f"find {self._working_dir}/{remote_dir} -type f",
            warn=True,
            out_stream=stream,
            err_stream=stream,
        )

        if result.exited != 0:
            raise RuntimeError()

        paths = [
            p.removeprefix(f"{self._working_dir}/")
            for p in stream.getvalue().strip().split("\n")
            if p
        ]
        return paths

    def exec(self, cmd: str, env: dict[str, str] | None = None) -> ExecResult:
        stream = io.StringIO()
        result = self._conn.run(
            f"cd {self._working_dir} && {cmd}",
            warn=True,
            out_stream=stream,
            err_stream=stream,
            env=env,
        )
        return ExecResult(result.exited or 0, stream.getvalue().strip())

    def destroy(self):
        self._conn.run(f"find {self._working_dir} -mindepth 1 -delete")
        self._conn.close()
