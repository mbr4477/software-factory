from .hatchet_provider import hatchet
from .tasks import container_job_task, pipeline_task, remote_ssh_job_task


def main():
    worker = hatchet.worker(
        name="worker",
        workflows=[pipeline_task, container_job_task, remote_ssh_job_task],
    )
    worker.start()
