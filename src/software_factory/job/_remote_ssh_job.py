import io
import os
import tempfile
import traceback

import fabric

from ..artifacts import ArtifactStore
from ._base_job_input import BaseJobInput
from ._result import Result


class RemoteSshJobInput(BaseJobInput):
    hostname: str
    user: str
    working_dir: str
    port: int = 22


class RemoteSshJob:
    def __init__(self, artifact_store: ArtifactStore):
        self._artifact_store = artifact_store

    def run(self, job: RemoteSshJobInput) -> Result:
        exit_code = -1
        out_artifacts = None
        code_dir = f"{job.working_dir}/code"
        clone_script = [
            f"rm -rf {code_dir}",
            f"git clone -b {job.branch_name} {job.git_url} {code_dir}",
            f"cd {code_dir}",
        ]

        logs = []
        with fabric.Connection(
            job.hostname, job.user, job.port, forward_agent=True
        ) as conn:
            try:
                out_stream = io.StringIO()
                result = conn.run(
                    " && ".join(clone_script),
                    warn=True,
                    out_stream=out_stream,
                    err_stream=out_stream,
                    env={
                        k: v or os.environ.get(k, "") for k, v in job.variables.items()
                    },
                    replace_env=True,
                )
                if result.exited != 0:
                    # Clone failed
                    logs = out_stream.getvalue().split("\n")
                    return Result(exit_code=result.exited, logs=logs)

                if job.load_artifacts:
                    for object_key, path in job.load_artifacts.items():
                        with tempfile.TemporaryDirectory() as tmpdir:
                            local_path = os.path.join(tmpdir, os.path.basename(path))
                            remote_path = f"{code_dir}/{path}"
                            remote_dir = os.path.dirname(remote_path)
                            self._artifact_store.get_object(object_key, local_path)
                            _ = conn.run(f"mkdir -p {remote_dir}")
                            _ = conn.put(local_path, f"{code_dir}/{path}")
                            os.remove(local_path)

                # Run the job script
                result = conn.run(
                    " && ".join([f"cd {code_dir}"] + job.script),
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

                if job.artifacts:
                    out_artifacts = {}
                    with tempfile.TemporaryDirectory() as tmpdir:
                        for path in job.artifacts.paths:
                            # Get all the files we need to copy
                            result = conn.run(f"cd {code_dir} && find {path} -type f")
                            files = result.stdout.strip().split("\n")
                            for f in files:
                                local_path = os.path.join(tmpdir, f)
                                local_dir = os.path.dirname(local_path)
                                os.makedirs(local_dir, exist_ok=True)
                                _ = conn.get(f"{code_dir}/{f}", local=local_path)
                                key = f"{job.uid}/{f}"
                                self._artifact_store.put_object(key, local_path)
                                out_artifacts[key] = f

            except Exception as e:  # noqa: BLE001
                traceback.print_tb(e.__traceback__)
                print(str(e))
            finally:
                _ = conn.run(f"rm -rf {job.working_dir}/code", warn=True)
        return Result(exit_code=exit_code, logs=logs, artifacts=out_artifacts)
