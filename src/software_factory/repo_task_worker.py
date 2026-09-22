from software_factory.hatchet_provider import hatchet
from software_factory.tasks.container_repo_task import container_repo_task
from software_factory.tasks.ssh_repo_task import ssh_repo_task


def main():
    worker = hatchet.worker(
        name="repo-task-worker",
        workflows=[container_repo_task, ssh_repo_task],
    )
    worker.start()
