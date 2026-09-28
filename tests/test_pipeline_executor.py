import asyncio
from collections.abc import Iterable
from unittest import mock

from software_factory.pipeline import (
    ContainerJob,
    Pipeline,
    PipelineExecutor,
    RemoteSshJob,
    Result,
)


def test_runs_successful_stages_to_completion():
    scan_job = ContainerJob(
        name="scan-job",
        type="container",
        stage="scan",
        git_url="git@giturl.git",
        script=["echo 'scan'"],
        image="alpine:latest",
    )
    build_job = ContainerJob(
        name="build-job",
        type="container",
        stage="build",
        git_url="git@giturl.git",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job = ContainerJob(
        name="test-job",
        type="container",
        stage="test",
        git_url="git@giturl.git",
        script=["echo 'test'"],
        image="alpine:latest",
    )

    pipeline = Pipeline(
        max_backtracks=1,
        stages=["scan", "build", "test"],
        jobs={"scan-job": scan_job, "build-job": build_job, "test-job": test_job},
    )

    engine = mock.AsyncMock()
    engine.spawn_container_job.return_value = Result(exit_code=0)
    engine.spawn_remote_ssh_job.return_value = Result(exit_code=0)

    uut = PipelineExecutor(pipeline, engine)
    asyncio.run(uut.execute())

    engine.assert_has_calls(
        [
            mock.call.spawn_container_job(scan_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
        ]
    )


def test_backtracks_on_failure():
    scan_job = ContainerJob(
        name="scan-job",
        type="container",
        stage="scan",
        git_url="git@giturl.git",
        script=["echo 'scan'"],
        image="alpine:latest",
    )
    build_job = ContainerJob(
        name="build-job",
        type="container",
        stage="build",
        git_url="git@giturl.git",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job = ContainerJob(
        name="test-job",
        type="container",
        stage="test",
        git_url="git@giturl.git",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="build",
    )

    pipeline = Pipeline(
        stages=["scan", "build", "test"],
        max_backtracks=1,
        jobs={"scan-job": scan_job, "build-job": build_job, "test-job": test_job},
    )

    engine = mock.AsyncMock()

    test_spawn_count = 0

    async def spawn_container_job(job: ContainerJob) -> Result:
        nonlocal test_spawn_count
        if job == test_job:
            test_spawn_count += 1
        return (
            Result(exit_code=1)
            if job == test_job and test_spawn_count == 1
            else Result(exit_code=0)
        )

    engine.spawn_container_job.side_effect = spawn_container_job

    uut = PipelineExecutor(pipeline, engine)
    asyncio.run(uut.execute())

    engine.assert_has_calls(
        [
            mock.call.spawn_container_job(scan_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
        ]
    )


def test_backtracks_to_earliest_stage():
    scan_job = ContainerJob(
        name="scan-job",
        type="container",
        stage="scan",
        git_url="git@giturl.git",
        script=["echo 'scan'"],
        image="alpine:latest",
    )
    build_job = ContainerJob(
        name="build-job",
        type="container",
        stage="build",
        git_url="git@giturl.git",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job1 = ContainerJob(
        name="test-job1",
        type="container",
        stage="test",
        git_url="git@giturl.git",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="build",
    )
    test_job2 = ContainerJob(
        name="test-job2",
        type="container",
        stage="test",
        git_url="git@giturl.git",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="scan",
    )

    pipeline = Pipeline(
        stages=["scan", "build", "test"],
        max_backtracks=1,
        jobs={
            "scan-job": scan_job,
            "build-job": build_job,
            "test-job1": test_job1,
            "test-job2": test_job2,
        },
    )

    engine = mock.AsyncMock()

    test1_spawn_count = 0
    test2_spawn_count = 0

    def spawn_container_job(job: ContainerJob) -> Result:
        nonlocal test1_spawn_count
        nonlocal test2_spawn_count

        if job == test_job1:
            test1_spawn_count += 1
            return (
                Result(exit_code=1) if test1_spawn_count == 1 else Result(exit_code=0)
            )

        if job == test_job2:
            test2_spawn_count += 1
            return (
                Result(exit_code=1) if test2_spawn_count == 1 else Result(exit_code=0)
            )

        return Result(exit_code=0)

    engine.spawn_container_job.side_effect = spawn_container_job

    uut = PipelineExecutor(pipeline, engine)
    asyncio.run(uut.execute())

    engine.assert_has_calls(
        [
            mock.call.spawn_container_job(scan_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job1),
            mock.call.spawn_container_job(test_job2),
            mock.call.spawn_container_job(scan_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job1),
            mock.call.spawn_container_job(test_job2),
        ]
    )


def test_limits_backtracks_to_max():
    build_job = ContainerJob(
        name="build-job",
        type="container",
        stage="build",
        git_url="git@giturl.git",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job = ContainerJob(
        name="test-job",
        type="container",
        stage="test",
        git_url="git@giturl.git",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="build",
    )

    pipeline = Pipeline(
        max_backtracks=2,
        stages=["build", "test"],
        jobs={"build-job": build_job, "test-job": test_job},
    )

    engine = mock.AsyncMock()
    engine.spawn_container_job.side_effect = lambda job: (
        Result(exit_code=1) if job == test_job else Result(exit_code=0)
    )

    uut = PipelineExecutor(pipeline, engine)
    asyncio.run(uut.execute())

    # Max backtracks of 2 means all jobs can run up to 3 times
    engine.assert_has_calls(
        [
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
            mock.call.spawn_container_job(build_job),
            mock.call.spawn_container_job(test_job),
        ]
    )
