from pydantic import BaseModel


class BaseRunnerInput(BaseModel):
    git_repo_url: str
    git_branch_name: str
    script: list[str]
    before_script: list[str] | None = None
    env: dict[str, str] = {}


class RunnerOutput(BaseModel):
    success: bool
    logs: list[str]
