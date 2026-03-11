"""CI debug environment — clones repo at failed commit and fetches logs."""

import logging
import re

from github.actions.git_utils import clone_url, run_git
from github.client import GitHubClient
from shared.types import ToolResult

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"ghp_[A-Za-z0-9]+|gho_[A-Za-z0-9]+|Bearer\s+\S+", re.IGNORECASE)


class CIEnvironment:
    """Sets up a local environment for debugging CI failures.

    Clones the repo at the failed commit SHA and collects
    failure logs from each failed job.
    """

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    async def setup(
        self,
        repo: str,
        run_id: int,
        target_dir: str,
    ) -> ToolResult:
        """Clone repo at failed SHA and gather failure context."""
        run_data = await self._client.get_run(repo, run_id)

        if run_data["conclusion"] != "failure":
            return ToolResult(
                success=True,
                data={
                    "run_id": run_data["run_id"],
                    "conclusion": run_data["conclusion"],
                    "skipped": True,
                    "message": "No failure to debug",
                },
            )

        sha = run_data["sha"]
        url = clone_url(repo)

        success, output = await run_git("clone", "--depth=50", url, target_dir)
        if not success:
            return ToolResult(success=False, error=f"Clone failed: {output}")

        success, output = await run_git("checkout", sha, cwd=target_dir)
        if not success:
            return ToolResult(success=False, error=f"Checkout failed: {output}")

        failed_jobs = []
        for job in run_data.get("failed_jobs", []):
            log = await self._fetch_job_log(repo, job["id"])
            failed_jobs.append({
                "name": job["name"],
                "conclusion": job["conclusion"],
                "log": _sanitize(log),
            })

        return ToolResult(
            success=True,
            data={
                "run_id": run_data["run_id"],
                "sha": sha,
                "conclusion": "failure",
                "url": run_data.get("url", ""),
                "target_dir": target_dir,
                "failed_jobs": failed_jobs,
            },
        )

    async def _fetch_job_log(self, repo: str, job_id: int) -> str:
        """Fetch log for a specific failed job by job ID.

        GitHub Actions logs endpoint returns plain text per job,
        not a ZIP archive, when requesting a single job's log.
        """
        try:
            return await self._client.get_job_log(repo, job_id)
        except Exception:
            logger.exception("Failed to fetch log for job %d", job_id)
            return f"Log unavailable for job: {job_id}"


def _sanitize(text: str) -> str:
    """Remove tokens from log output."""
    return _TOKEN_PATTERN.sub("[REDACTED]", text)
