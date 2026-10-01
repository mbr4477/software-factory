import asyncio

from ..job import Artifacts, ContainerJobInput, RemoteSshJobInput
from ._job_engine import JobEngine
from ._pipeline import PipelineDef


class PipelineExecutor:
    def __init__(self, engine: JobEngine):
        self._engine = engine

    async def execute(self, uid: str, pipeline: PipelineDef):
        counter = 0
        artifacts = {}
        next_stage_idx = 0
        num_stages = len(pipeline.stages)

        num_backtracks = 0
        while next_stage_idx < num_stages and num_backtracks <= pipeline.max_backtracks:
            stage = pipeline.stages[next_stage_idx]
            stage_jobs = {k: v for k, v in pipeline.jobs.items() if v.stage == stage}

            next_stage_idx += 1

            coros = []
            for job in stage_jobs.values():
                if job.type == "container":
                    inputs = ContainerJobInput(
                        uid=f"{uid}-{job.name}-{counter}",
                        name=job.name,
                        stage=job.stage,
                        git_url=job.git_url,
                        script=job.script,
                        branch_name=job.branch_name,
                        variables=job.variables,
                        artifacts=(
                            Artifacts(paths=job.artifacts.paths)
                            if job.artifacts
                            else None
                        ),
                        image=job.image,
                        entrypoint=job.entrypoint,
                        load_artifacts=artifacts,
                    )
                    coros.append(self._engine.spawn_container_job(inputs))
                elif job.type == "remote_ssh":
                    inputs = RemoteSshJobInput(
                        uid=f"{uid}-{job.name}-{counter}",
                        name=job.name,
                        stage=job.stage,
                        git_url=job.git_url,
                        script=job.script,
                        branch_name=job.branch_name,
                        variables=job.variables,
                        artifacts=(
                            Artifacts(paths=job.artifacts.paths)
                            if job.artifacts
                            else None
                        ),
                        hostname=job.hostname,
                        user=job.user,
                        working_dir=job.working_dir,
                        port=job.port,
                        load_artifacts=artifacts,
                    )
                    coros.append(self._engine.spawn_remote_ssh_job(inputs))

            results = zip(await asyncio.gather(*coros), stage_jobs.values())
            backtracking = False
            for result, job in results:
                if result.artifacts:
                    artifacts.update(result.artifacts)
                if result.exit_code != 0 and job.on_fail:
                    try:
                        on_fail_idx = pipeline.stages.index(job.on_fail)
                        if on_fail_idx < next_stage_idx:
                            backtracking = True
                            next_stage_idx = on_fail_idx
                    except ValueError:
                        # Ignore unknown stages in on_fail
                        pass

            if backtracking:
                num_backtracks += 1
