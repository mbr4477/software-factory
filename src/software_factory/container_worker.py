from .hatchet_provider import hatchet
from .tasks import container_job_task


def main():
    worker = hatchet.worker(name="container-worker", workflows=[container_job_task])
    worker.start()
