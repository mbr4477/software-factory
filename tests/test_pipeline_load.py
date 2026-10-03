from software_factory.pipeline import (
    ContainerJobDef,
    PipelineDef,
    RemoteSshJobDef,
    pipeline_def_from_dict,
)


def test_loads_minimal():
    inputs = {"stages": ["first", "second", "third"], "max_backtracks": 1}
    result = pipeline_def_from_dict(inputs)
    assert result == PipelineDef(stages=["first", "second", "third"], max_backtracks=1)


def test_loads_container_job_with_required_fields():
    inputs = {
        "stages": ["first", "second"],
        "max_backtracks": 2,
        "first-job": {
            "stage": "first",
            "type": "container",
            "git_url": "git@github.com:mbr4477/software-factory.git",
            "image": "alpine:latest",
            "script": ["echo 'Hello, World!'"],
        },
    }
    result = pipeline_def_from_dict(inputs)
    assert result == PipelineDef(
        stages=["first", "second"],
        max_backtracks=2,
        jobs={
            "first-job": ContainerJobDef(
                name="first-job",
                type="container",
                stage="first",
                script=["echo 'Hello, World!'"],
                image="alpine:latest",
            )
        },
    )


def test_loads_remote_ssh_job_with_required_fields():
    inputs = {
        "stages": ["first", "second"],
        "max_backtracks": 3,
        "first-job": {
            "stage": "first",
            "type": "remote_ssh",
            "script": ["echo 'Hello, World!'"],
            "hostname": "localhost",
            "user": "default",
            "working_dir": "/home/default/workspace",
        },
    }
    result = pipeline_def_from_dict(inputs)
    assert result == PipelineDef(
        stages=["first", "second"],
        max_backtracks=3,
        jobs={
            "first-job": RemoteSshJobDef(
                name="first-job",
                type="remote_ssh",
                stage="first",
                script=["echo 'Hello, World!'"],
                hostname="localhost",
                user="default",
                working_dir="/home/default/workspace",
            )
        },
    )
