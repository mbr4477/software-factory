from .hatchet_provider import hatchet
from .tasks import remote_ssh_job_task


def main():
    worker = hatchet.worker(name="remote-ssh-worker", workflows=[remote_ssh_job_task])
    worker.start()
