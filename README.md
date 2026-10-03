# Software Factory

A tool for running pipelines of jobs in different execution environments.
Pipelines are *not* DAGs and can loop back to previous stages if a job fails.
The following execution environments are supported:
- **Containers.** Run job scripts in containers.
- **Remote SSH.** Run job scripts on remote SSH hosts.

## Tech Stack

- **[Hatchet.](https://hatchet.run)** Job orchestration and durability.
- **[RustFS.](https://rustfs.com)** S3 storage for job artifacts.
- **Docker** (or other compatible container runtime). Container-based job execution.

## Getting Started

1. Start compose to spin up Hatchet (job orchestration) and RustFS (S3 storage for job artifacts):
   ```shell
   docker compose up -d
   ```
2. Log into Hatchet (http://localhost:8888) and generate a client token. The default credentials are `admin@example.com`/`Admin123!!`
3. Add the following environment variables wherever you run will run Hatchet workers (more on that below):
    ```shell
    # Change the hostname if you are accessing the Hatchet server from another machine on your LAN 
    export HATCHET_CLIENT_HOST_PORT=127.0.0.1:7077
    export HATCHET_CLIENT_TLS_STRATEGY=none
    export HATCHET_CLIENT_TOKEN=<your token here>
    export S3_ACCESS_KEY="rustfsadmin"
    export S3_SECRET_KEY="rustfsadmin"
    ```
4. Start the Hatchet workers that will pull and run queued jobs:
    ```shell
    # Run a single worker for all the tasks
    uv run worker

    # Run each task worker separately, if you need to run them in shells with different environment vars
    uv run pipeline-worker
    uv run container-worker
    uv run remote-ssh-worker
    ```
> [!note]
> If you have an SSH agent running on your host (`SSH_AUTH_SOCKET` defined in the environment), container and remote SSH jobs will attempt to forward this agent to the execution environment.
5. Trigger a pipeline:
   ```shell
   uv run trigger my_pipeline.yaml
   ```
6. Artifacts can be viewed and downloaded from https://localhost:9001 (credentials: `rustfsadmin`/`rustfsadmin`). Job artifacts are *not* automatically removed on any schedule. A custom schedule can be configured in RustFS or artifacts manually cleaned when necessary.

## Pipeline YAML 

See [schema/pipeline.schema.json](schema/pipeline.schema.json) for the pipeline YAML schema.



