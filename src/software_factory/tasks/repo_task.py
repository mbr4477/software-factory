from pydantic import BaseModel


class BaseRepoTaskInput(BaseModel):
    git_repo_url: str
    git_branch_name: str
    script: list[str]
    before_script: list[str] | None = None

    env: dict[str, str | None] = {}
    """If a variable maps to null, the value in the runner's environment is used."""


class RepoTaskOutput(BaseModel):
    success: bool
    logs: list[str]
