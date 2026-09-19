from software_factory.hatchet_provider import hatchet
from software_factory.tasks.container_runner import container_runner
from software_factory.tasks.ssh_runner import ssh_runner


def main():
    worker = hatchet.worker(
        name="runner-worker",
        workflows=[container_runner, ssh_runner],
    )
    worker.start()
