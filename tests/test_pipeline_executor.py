import asyncio
from unittest import mock

from software_factory.job import (
    BaseJobInput,
    ContainerJobInput,
    Result,
)
from software_factory.pipeline import (
    ContainerJobDef,
    PipelineDef,
    PipelineExecutor,
)

SCAN_JOB_DEF = ContainerJobDef(
    name="scan-job",
    type="container",
    stage="scan",
    script=["echo 'scan'"],
    image="alpine:latest",
)
BUILD_JOB_DEF = ContainerJobDef(
    name="build-job",
    type="container",
    stage="build",
    script=["echo 'build'"],
    image="alpine:latest",
)
TEST_JOB_DEF = ContainerJobDef(
    name="test-job",
    type="container",
    stage="test",
    script=["echo 'test'"],
    image="alpine:latest",
    on_fail="build",
)


class JobInputWithName:
    def __init__(self, name: str):
        self._name = name

    def __eq__(self, job_def: object) -> bool:
        return isinstance(job_def, BaseJobInput) and self._name == job_def.name


def test_runs_successful_stages_to_completion():
    pipeline = PipelineDef(
        max_backtracks=1,
        stages=["scan", "build", "test"],
        jobs={
            "scan-job": SCAN_JOB_DEF,
            "build-job": BUILD_JOB_DEF,
            "test-job": TEST_JOB_DEF,
        },
    )

    dispatcher = mock.AsyncMock()
    dispatcher.dispatch_container_job.return_value = Result(exit_code=0)

    uut = PipelineExecutor(dispatcher)
    asyncio.run(uut.execute("abc123", pipeline))

    dispatcher.assert_has_calls(
        [
            mock.call.dispatch_container_job(JobInputWithName("scan-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
        ]
    )


def test_backtracks_on_failure():
    pipeline = PipelineDef(
        stages=["scan", "build", "test"],
        max_backtracks=1,
        jobs={
            "scan-job": SCAN_JOB_DEF,
            "build-job": BUILD_JOB_DEF,
            "test-job": TEST_JOB_DEF,
        },
    )

    dispatcher = mock.AsyncMock()

    test_spawn_count = 0

    async def dispatch_container_job(job: ContainerJobInput) -> Result:
        nonlocal test_spawn_count
        if job.name == "test-job":
            test_spawn_count += 1
        return (
            Result(exit_code=1)
            if job.name == "test-job" and test_spawn_count == 1
            else Result(exit_code=0)
        )

    dispatcher.dispatch_container_job.side_effect = dispatch_container_job

    uut = PipelineExecutor(dispatcher)
    asyncio.run(uut.execute("abc123", pipeline))

    dispatcher.assert_has_calls(
        [
            mock.call.dispatch_container_job(JobInputWithName("scan-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
        ]
    )


def test_backtracks_to_earliest_stage():
    scan_job = ContainerJobDef(
        name="scan-job",
        type="container",
        stage="scan",
        script=["echo 'scan'"],
        image="alpine:latest",
    )
    build_job = ContainerJobDef(
        name="build-job",
        type="container",
        stage="build",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job1 = ContainerJobDef(
        name="test-job1",
        type="container",
        stage="test",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="build",
    )
    test_job2 = ContainerJobDef(
        name="test-job2",
        type="container",
        stage="test",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="scan",
    )

    pipeline = PipelineDef(
        stages=["scan", "build", "test"],
        max_backtracks=1,
        jobs={
            "scan-job": scan_job,
            "build-job": build_job,
            "test-job1": test_job1,
            "test-job2": test_job2,
        },
    )

    dispatcher = mock.AsyncMock()

    test1_spawn_count = 0
    test2_spawn_count = 0

    def dispatch_container_job(job: ContainerJobInput) -> Result:
        nonlocal test1_spawn_count
        nonlocal test2_spawn_count

        if job.name == "test-job1":
            test1_spawn_count += 1
            return (
                Result(exit_code=1) if test1_spawn_count == 1 else Result(exit_code=0)
            )

        if job.name == "test-job2":
            test2_spawn_count += 1
            return (
                Result(exit_code=1) if test2_spawn_count == 1 else Result(exit_code=0)
            )

        return Result(exit_code=0)

    dispatcher.dispatch_container_job.side_effect = dispatch_container_job

    uut = PipelineExecutor(dispatcher)
    asyncio.run(uut.execute("abc123", pipeline))

    dispatcher.assert_has_calls(
        [
            mock.call.dispatch_container_job(JobInputWithName("scan-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job1")),
            mock.call.dispatch_container_job(JobInputWithName("test-job2")),
            mock.call.dispatch_container_job(JobInputWithName("scan-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job1")),
            mock.call.dispatch_container_job(JobInputWithName("test-job2")),
        ]
    )


def test_limits_backtracks_to_max():
    build_job = ContainerJobDef(
        name="build-job",
        type="container",
        stage="build",
        script=["echo 'build'"],
        image="alpine:latest",
    )
    test_job = ContainerJobDef(
        name="test-job",
        type="container",
        stage="test",
        script=["echo 'test'"],
        image="alpine:latest",
        on_fail="build",
    )

    pipeline = PipelineDef(
        max_backtracks=2,
        stages=["build", "test"],
        jobs={"build-job": build_job, "test-job": test_job},
    )

    dispatcher = mock.AsyncMock()
    dispatcher.dispatch_container_job.side_effect = lambda job: (
        Result(exit_code=1) if job.name == "test-job" else Result(exit_code=0)
    )

    uut = PipelineExecutor(dispatcher)
    asyncio.run(uut.execute("abc123", pipeline))

    # Max backtracks of 2 means all jobs can run up to 3 times
    dispatcher.assert_has_calls(
        [
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
            mock.call.dispatch_container_job(JobInputWithName("build-job")),
            mock.call.dispatch_container_job(JobInputWithName("test-job")),
        ]
    )
