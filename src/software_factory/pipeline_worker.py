from .hatchet_provider import hatchet
from .tasks import pipeline_task


def main():
    worker = hatchet.worker(name="pipeline-worker", workflows=[pipeline_task])
    worker.start()
