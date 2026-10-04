import os
from unittest import mock

from software_factory.job import Artifacts, BaseJobInput, JobExecutor, Result
from software_factory.job_runtime._job_runtime import ExecResult


def make_job(**overrides) -> BaseJobInput:
    values = {
        "uid": "job-123",
        "name": "example",
        "stage": "test",
        "script": ["echo hello", "run-tests"],
    }
    values.update(overrides)
    return BaseJobInput(**values)


def test_executes_joined_script_and_returns_split_logs_without_artifacts():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(
        exit_code=7, stdout="first line\nsecond line\n"
    )
    artifact_store = mock.Mock()
    job = make_job(variables={"MODE": "test"})

    result = JobExecutor(runtime, artifact_store).run(job)

    runtime.exec.assert_called_once_with("echo hello && run-tests", {"MODE": "test"})
    assert result == Result(
        exit_code=7,
        logs=["first line", "second line", ""],
        artifacts=None,
    )
    runtime.is_dir.assert_not_called()
    runtime.list_tree.assert_not_called()
    runtime.get_file.assert_not_called()
    runtime.put_file.assert_not_called()
    artifact_store.get_object.assert_not_called()
    artifact_store.put_object.assert_not_called()


def test_loads_artifacts_into_runtime_and_removes_temporary_files():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="done")
    artifact_store = mock.Mock()
    job = make_job(
        load_artifacts={
            "artifact-one": "/workspace/input.txt",
            "artifact-two": "nested/config.yml",
        }
    )

    # Avoid invoking the filesystem operation while still checking the intended cleanup.
    with mock.patch("software_factory.job._job_executor.os.remove") as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    runtime.exec.assert_called_once_with("echo hello && run-tests", None)
    assert result.logs == ["done"]
    assert result.artifacts is None
    assert artifact_store.get_object.call_count == 2

    downloads = {
        call.args[0]: call.args[1]
        for call in artifact_store.get_object.call_args_list
    }
    assert set(downloads) == {"artifact-one", "artifact-two"}
    assert os.path.basename(downloads["artifact-one"]) == "input.txt"
    assert os.path.basename(downloads["artifact-two"]) == "config.yml"
    assert os.path.dirname(downloads["artifact-one"]) == os.path.dirname(
        downloads["artifact-two"]
    )
    runtime.put_file.assert_has_calls(
        [
            mock.call(downloads["artifact-one"], "/workspace/input.txt"),
            mock.call(downloads["artifact-two"], "nested/config.yml"),
        ]
    )
    assert remove.call_args_list == [
        mock.call(downloads["artifact-one"]),
        mock.call(downloads["artifact-two"]),
    ]
    artifact_store.put_object.assert_not_called()


def test_collects_files_from_artifact_paths_and_skips_missing_files():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="ok\n")
    runtime.is_dir.side_effect = lambda path: path == "/workspace/output"
    runtime.list_tree.return_value = [
        "/workspace/output/result.json",
        "/workspace/output/missing.txt",
    ]

    def get_file(remote_path, _local_path):
        if remote_path.endswith("missing.txt"):
            raise FileNotFoundError(remote_path)

    runtime.get_file.side_effect = get_file
    artifact_store = mock.Mock()
    job = make_job(
        artifacts=Artifacts(paths=["/workspace/single.log", "/workspace/output"])
    )

    with mock.patch("software_factory.job._job_executor.os.remove") as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    runtime.is_dir.assert_has_calls(
        [mock.call("/workspace/single.log"), mock.call("/workspace/output")]
    )
    runtime.list_tree.assert_called_once_with("/workspace/output")
    assert [call.args[0] for call in runtime.get_file.call_args_list] == [
        "/workspace/single.log",
        "/workspace/output/result.json",
        "/workspace/output/missing.txt",
    ]

    stored = artifact_store.put_object.call_args_list
    assert [call.args[0] for call in stored] == [
        "job-123//workspace/single.log",
        "job-123//workspace/output/result.json",
    ]
    assert [os.path.basename(call.args[1]) for call in stored] == [
        "single.log",
        "result.json",
    ]
    assert result == Result(
        exit_code=0,
        logs=["ok", ""],
        artifacts={
            "job-123//workspace/single.log": "/workspace/single.log",
            "job-123//workspace/output/result.json": "/workspace/output/result.json",
        },
    )
    # Files are removed only after both download and artifact storage succeed.
    assert remove.call_count == 2
    assert [call.args[0] for call in remove.call_args_list] == [
        stored[0].args[1],
        stored[1].args[1],
    ]


def test_artifact_storage_file_not_found_is_ignored():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="")
    runtime.is_dir.return_value = False
    artifact_store = mock.Mock()
    artifact_store.put_object.side_effect = FileNotFoundError(
        "temporary file vanished"
    )
    job = make_job(artifacts=Artifacts(paths=["/workspace/result.txt"]))

    with mock.patch("software_factory.job._job_executor.os.remove") as remove:
        result = JobExecutor(runtime, artifact_store).run(job)

    artifact_store.put_object.assert_called_once()
    assert result.artifacts == {}
    remove.assert_not_called()


def test_empty_artifact_path_list_returns_empty_artifact_mapping():
    runtime = mock.Mock()
    runtime.exec.return_value = ExecResult(exit_code=0, stdout="")
    artifact_store = mock.Mock()

    result = JobExecutor(runtime, artifact_store).run(
        make_job(artifacts=Artifacts(paths=[]))
    )

    assert result.artifacts == {}
    runtime.is_dir.assert_not_called()
    runtime.list_tree.assert_not_called()
    runtime.get_file.assert_not_called()
    artifact_store.put_object.assert_not_called()
