from unittest import mock

from software_factory.job import Artifacts, BaseJobInput, JobExecutor, Result
from software_factory.job_runtime import ExecResult


TEMP_DIR = "/tmp/job-executor-test"


def make_job(**kwargs) -> BaseJobInput:
    values = {
        "uid": "job-123",
        "name": "example-job",
        "stage": "test",
        "script": ["echo first", "echo second"],
    }
    values.update(kwargs)
    return BaseJobInput(**values)


def patch_temporary_directory():
    temporary_directory = mock.MagicMock()
    temporary_directory.__enter__.return_value = TEMP_DIR
    return mock.patch(
        "software_factory.job._job_executor.tempfile.TemporaryDirectory",
        return_value=temporary_directory,
    )


def test_loads_artifacts_into_runtime_and_removes_temporary_files():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="done")
    artifact_store = mock.Mock()
    job = make_job(
        load_artifacts={
            "source/object-one": "/workspace/input.txt",
            "source/object-two": "relative/config.yml",
        }
    )

    with patch_temporary_directory(), mock.patch(
        "software_factory.job._job_executor.os.remove"
    ) as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    artifact_store.get_object.assert_has_calls(
        [
            mock.call("source/object-one", f"{TEMP_DIR}/input.txt"),
            mock.call("source/object-two", f"{TEMP_DIR}/config.yml"),
        ]
    )
    runtime.put_file.assert_has_calls(
        [
            mock.call(f"{TEMP_DIR}/input.txt", "/workspace/input.txt"),
            mock.call(f"{TEMP_DIR}/config.yml", "relative/config.yml"),
        ]
    )
    assert remove.call_args_list == [
        mock.call(f"{TEMP_DIR}/input.txt"),
        mock.call(f"{TEMP_DIR}/config.yml"),
    ]
    assert result.artifacts is None


def test_executes_joined_script_and_returns_stdout_lines_and_exit_code():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=7, stdout="first\nsecond\n")
    artifact_store = mock.Mock()
    job = make_job(script=["echo first", "echo second"], variables={"MODE": "fast"})

    result = JobExecutor(runtime, artifact_store).run(job)

    runtime.exec.assert_called_once_with("echo first && echo second", {"MODE": "fast"})
    assert result == Result(exit_code=7, logs=["first", "second", ""], artifacts=None)
    artifact_store.get_object.assert_not_called()
    artifact_store.put_object.assert_not_called()
    runtime.is_dir.assert_not_called()


def test_exports_files_and_directory_contents_as_artifacts():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="")
    runtime.is_dir.side_effect = lambda path: path == "/workspace/reports"
    runtime.list_tree.return_value = [
        "/workspace/reports/summary.txt",
        "/workspace/reports/details.json",
    ]
    artifact_store = mock.Mock()
    job = make_job(
        artifacts=Artifacts(paths=["/workspace/reports", "/workspace/standalone.log"])
    )

    with patch_temporary_directory(), mock.patch(
        "software_factory.job._job_executor.os.remove"
    ) as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    runtime.is_dir.assert_has_calls(
        [mock.call("/workspace/reports"), mock.call("/workspace/standalone.log")]
    )
    runtime.list_tree.assert_called_once_with("/workspace/reports")
    artifact_store.put_object.assert_has_calls(
        [
            mock.call(
                "job-123//workspace/reports/summary.txt",
                f"{TEMP_DIR}/summary.txt",
            ),
            mock.call(
                "job-123//workspace/reports/details.json",
                f"{TEMP_DIR}/details.json",
            ),
            mock.call("job-123//workspace/standalone.log", f"{TEMP_DIR}/standalone.log"),
        ]
    )
    assert result.artifacts == {
        "job-123//workspace/reports/summary.txt": "/workspace/reports/summary.txt",
        "job-123//workspace/reports/details.json": "/workspace/reports/details.json",
        "job-123//workspace/standalone.log": "/workspace/standalone.log",
    }
    assert remove.call_args_list == [
        mock.call(f"{TEMP_DIR}/summary.txt"),
        mock.call(f"{TEMP_DIR}/details.json"),
        mock.call(f"{TEMP_DIR}/standalone.log"),
    ]


def test_ignores_artifacts_that_cannot_be_retrieved_from_runtime():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="")
    runtime.is_dir.return_value = False
    runtime.get_file.side_effect = FileNotFoundError
    artifact_store = mock.Mock()
    job = make_job(artifacts=Artifacts(paths=["/workspace/missing.txt"]))

    with patch_temporary_directory(), mock.patch(
        "software_factory.job._job_executor.os.remove"
    ) as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    assert result.artifacts == {}
    runtime.get_file.assert_called_once_with(
        "/workspace/missing.txt", f"{TEMP_DIR}/missing.txt"
    )
    artifact_store.put_object.assert_not_called()
    remove.assert_not_called()
