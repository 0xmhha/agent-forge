"""GitHub API client — read-only access, tokens never exposed in responses."""

from typing import Any

import httpx

_GITHUB_API = "https://api.github.com"


class GitHubClient:
    """Wraps the GitHub REST API with read-only operations.

    Supports both PAT and OAuth tokens. Auth header is stored
    internally and never included in return values.
    """

    def __init__(self, token: str) -> None:
        self._auth_header = f"Bearer {token}"

    async def list_issues(
        self,
        repo: str,
        state: str = "open",
        labels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List issues for a repo. Returns simplified metadata."""
        params: dict[str, Any] = {"state": state, "per_page": 30}
        if labels:
            params["labels"] = ",".join(labels)

        raw = await self._request("GET", f"{_GITHUB_API}/repos/{repo}/issues", params=params)
        return [_extract_issue(item) for item in raw]

    async def get_issue(self, repo: str, issue_number: int) -> dict[str, Any]:
        """Get full issue detail including body."""
        raw = await self._request("GET", f"{_GITHUB_API}/repos/{repo}/issues/{issue_number}")
        return _extract_issue_detail(raw)

    async def list_prs(
        self,
        repo: str,
        state: str = "open",
    ) -> list[dict[str, Any]]:
        """List pull requests for a repo."""
        params = {"state": state, "per_page": 30}
        raw = await self._request("GET", f"{_GITHUB_API}/repos/{repo}/pulls", params=params)
        return [_extract_pr(item) for item in raw]

    async def get_pr(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Get PR detail including changed files."""
        raw = await self._request("GET", f"{_GITHUB_API}/repos/{repo}/pulls/{pr_number}")
        files = await self._request("GET", f"{_GITHUB_API}/repos/{repo}/pulls/{pr_number}/files")
        result = _extract_pr_detail(raw)
        result["files"] = [_extract_file(f) for f in files]
        return result

    async def get_run(self, repo: str, run_id: int) -> dict[str, Any]:
        """Get a specific workflow run by ID, including failed jobs."""
        run = await self._request(
            "GET", f"{_GITHUB_API}/repos/{repo}/actions/runs/{run_id}"
        )

        failed_jobs: list[dict[str, Any]] = []
        if run.get("conclusion") == "failure":
            jobs_data = await self._request(
                "GET",
                f"{_GITHUB_API}/repos/{repo}/actions/runs/{run_id}/jobs",
            )
            failed_jobs = [
                {"id": job["id"], "name": job["name"], "conclusion": job["conclusion"]}
                for job in jobs_data.get("jobs", [])
                if job.get("conclusion") == "failure"
            ]

        return {
            "run_id": run["id"],
            "sha": run.get("head_sha", ""),
            "conclusion": run.get("conclusion", "pending"),
            "url": run.get("html_url", ""),
            "failed_jobs": failed_jobs,
        }

    async def get_job_log(self, repo: str, job_id: int) -> str:
        """Fetch plain-text log for a single job."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_GITHUB_API}/repos/{repo}/actions/jobs/{job_id}/logs",
                headers={
                    "Authorization": self._auth_header,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    async def get_ci_status(self, repo: str, ref: str) -> dict[str, Any]:
        """Get CI status for a commit ref (branch or SHA)."""
        runs_data = await self._request(
            "GET",
            f"{_GITHUB_API}/repos/{repo}/actions/runs",
            params={"head_sha": ref, "per_page": 1},
        )

        runs = runs_data.get("workflow_runs", [])
        if not runs:
            return {
                "run_id": None,
                "sha": ref,
                "conclusion": "neutral",
                "url": "",
                "failed_jobs": [],
            }

        run = runs[0]
        failed_jobs = []

        if run.get("conclusion") == "failure":
            jobs_data = await self._request(
                "GET",
                f"{_GITHUB_API}/repos/{repo}/actions/runs/{run['id']}/jobs",
            )
            failed_jobs = [
                {"name": job["name"], "conclusion": job["conclusion"]}
                for job in jobs_data.get("jobs", [])
                if job.get("conclusion") == "failure"
            ]

        return {
            "run_id": run["id"],
            "sha": ref,
            "conclusion": run.get("conclusion", "pending"),
            "url": run.get("html_url", ""),
            "failed_jobs": failed_jobs,
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send authenticated request to GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers={
                    "Authorization": self._auth_header,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                params=params,
            )
            response.raise_for_status()
            return response.json()


def _extract_issue(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract simplified issue metadata."""
    return {
        "number": raw["number"],
        "title": raw["title"],
        "author": raw.get("user", {}).get("login", ""),
        "state": raw["state"],
        "labels": [label["name"] for label in raw.get("labels", [])],
        "url": raw.get("html_url", ""),
        "created_at": raw.get("created_at", ""),
        "comment_count": raw.get("comments", 0),
    }


def _extract_issue_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract full issue detail."""
    result = _extract_issue(raw)
    result["body"] = raw.get("body", "")
    result["assignees"] = [a["login"] for a in raw.get("assignees", [])]
    return result


def _extract_pr(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract simplified PR metadata."""
    return {
        "number": raw["number"],
        "title": raw["title"],
        "author": raw.get("user", {}).get("login", ""),
        "state": raw["state"],
        "head_branch": raw.get("head", {}).get("ref", ""),
        "base_branch": raw.get("base", {}).get("ref", ""),
        "url": raw.get("html_url", ""),
        "draft": raw.get("draft", False),
        "created_at": raw.get("created_at", ""),
    }


def _extract_pr_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract full PR detail."""
    result = _extract_pr(raw)
    result["body"] = raw.get("body", "")
    result["additions"] = raw.get("additions", 0)
    result["deletions"] = raw.get("deletions", 0)
    result["changed_files"] = raw.get("changed_files", 0)
    result["merged"] = raw.get("merged", False)
    result["mergeable"] = raw.get("mergeable")
    return result


def _extract_file(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract changed file info."""
    return {
        "filename": raw["filename"],
        "status": raw["status"],
        "additions": raw.get("additions", 0),
        "deletions": raw.get("deletions", 0),
        "patch": raw.get("patch", ""),
    }
