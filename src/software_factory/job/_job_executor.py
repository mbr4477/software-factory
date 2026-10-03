import os
import tempfile

from ..artifacts import ArtifactStore
from ..job_runtime import JobRuntime
from ._base_job_input import BaseJobInput
from ._result import Result


class JobExecutor:
    def __init__(self, runtime: JobRuntime, artifact_store: ArtifactStore):
        self._runtime = runtime
        self._artifact_store = artifact_store

    def run(self, job: BaseJobInput) -> Result:
        if job.load_artifacts:
            with tempfile.TemporaryDirectory() as tmpdir:
                for object_key, path in job.load_artifacts.items():
                    local_path = os.path.join(tmpdir, os.path.basename(path))
                    self._artifact_store.get_object(object_key, local_path)
                    self._runtime.put_file(local_path, path)
                    os.remove(local_path)

        result = self._runtime.exec(" && ".join(job.script), job.variables)
        log_lines = result.stdout.split("\n")

        out_artifacts = None
        if job.artifacts:
            out_artifacts = {}
            with tempfile.TemporaryDirectory() as tmpdir:
                files = []
                for p in job.artifacts.paths:
                    if self._runtime.is_dir(p):
                        files.extend(self._runtime.list_tree(p))
                    else:
                        files.append(p)
                for f in files:
                    local_path = os.path.join(tmpdir, os.path.basename(f))
                    try:
                        self._runtime.get_file(f, local_path)
                        key = f"{job.uid}/{f}"
                        self._artifact_store.put_object(key, local_path)
                        out_artifacts[key] = f
                        os.remove(local_path)
                    except FileNotFoundError:
                        pass

        return Result(
            exit_code=result.exit_code, logs=log_lines, artifacts=out_artifacts
        )
