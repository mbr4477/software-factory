import asyncio

from .job_engine import JobEngine
from .pipeline_models import Pipeline


class PipelineExecutor:
    def __init__(
        self,
        pipeline: Pipeline,
        engine: JobEngine,
    ):
        self._pipeline = pipeline
        self._engine = engine

    async def execute(self):
        next_stage_idx = 0
        num_stages = len(self._pipeline.stages)

        num_backtracks = 0
        while (
            next_stage_idx < num_stages
            and num_backtracks <= self._pipeline.max_backtracks
        ):
            stage = self._pipeline.stages[next_stage_idx]
            stage_jobs = {
                k: v for k, v in self._pipeline.jobs.items() if v.stage == stage
            }

            next_stage_idx += 1

            coros = []
            for job in stage_jobs.values():
                if job.type == "container":
                    coros.append(self._engine.spawn_container_job(job))
                elif job.type == "remote_ssh":
                    coros.append(self._engine.spawn_remote_ssh_job(job))

            results = zip(await asyncio.gather(*coros), stage_jobs.values())
            backtracking = False
            for result, job in results:
                if result.exit_code != 0 and job.on_fail:
                    try:
                        on_fail_idx = self._pipeline.stages.index(job.on_fail)
                        if on_fail_idx < next_stage_idx:
                            backtracking = True
                            next_stage_idx = on_fail_idx
                    except ValueError:
                        # Ignore unknown stages in on_fail
                        pass

            if backtracking:
                num_backtracks += 1
