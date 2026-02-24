"""GitHub provider service for monthly contribution and organization stats."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
import logging

import requests

from src.config import AppConfig
from src.domain.models import GitHubContributionDay, GitHubMonthlyStats


class GitHubService:
	"""Fetch GitHub dashboard metrics using authenticated API requests.

	Private repository data is available only when `api_key` is configured and
	has sufficient repository read permissions.
	"""

	def __init__(self, config: AppConfig) -> None:
		"""Store GitHub source configuration.

		Args:
			config: Application configuration.
		"""

		self._username = config.github.username
		self._organization = config.github.organization
		self._api_key = config.github.api_key
		self._timeout_seconds = 12
		self._logger = logging.getLogger(self.__class__.__name__)

	def get_monthly_stats(self) -> GitHubMonthlyStats:
		"""Collect current-month GitHub metrics.

		Returns:
			Monthly GitHub statistics for dashboard rendering.
		"""

		now = datetime.now(UTC)
		month_start = date(year=now.year, month=now.month, day=1)
		month_label = month_start.strftime("%Y-%m")

		if not self._api_key:
			self._logger.warning(
				"github_api_key_missing private_repo_data_will_not_be_included"
			)
		daily_commits = self._fetch_user_monthly_commit_days(month_start)
		repo_count, org_commit_count, additions, deletions = self._fetch_org_monthly_stats(
			month_start
		)

		return GitHubMonthlyStats(
			month=month_label,
			contributions=daily_commits,
			organization_repo_count=repo_count,
			organization_monthly_commit_count=org_commit_count,
			organization_additions=additions,
			organization_deletions=deletions,
		)

	def _fetch_user_monthly_commit_days(
		self,
		month_start: date,
	) -> list[GitHubContributionDay]:
		"""Fetch user push-event commit counts for current month.

		Args:
			month_start: First day of month in UTC.

		Returns:
			Per-day commit counts from available events.
		"""

		if not self._username:
			return []

		headers = self._headers()
		try:
			response = requests.get(
				f"https://api.github.com/users/{self._username}/events/public",
				headers=headers,
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			events = response.json()
		except requests.RequestException:
			return []

		commit_counter: Counter[date] = Counter()
		for event in events:
			if event.get("type") != "PushEvent":
				continue
			created_at = event.get("created_at", "")
			try:
				event_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
			except ValueError:
				continue
			if event_date < month_start:
				continue
			commit_count = len(event.get("payload", {}).get("commits", []))
			commit_counter[event_date] += commit_count

		return [
			GitHubContributionDay(day=day, commit_count=count)
			for day, count in sorted(commit_counter.items(), key=lambda item: item[0])
		]

	def _fetch_org_monthly_stats(self, month_start: date) -> tuple[int, int, int, int]:
		"""Fetch organization repository and commit statistics.

		Args:
			month_start: First day of month in UTC.

		Returns:
			Tuple of repo count, commit count, additions, deletions.
		"""

		if not self._organization:
			return 0, 0, 0, 0

		headers = self._headers()
		repos = self._fetch_org_repositories(headers)
		if not repos:
			return 0, 0, 0, 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_commits = 0
		total_additions = 0
		total_deletions = 0

		for repo_name in repos:
			commits = self._fetch_repo_commits(repo_name, since=since, until=until, headers=headers)
			total_commits += len(commits)
			for commit_sha in commits:
				additions, deletions = self._fetch_commit_stats(
					repo_name=repo_name,
					commit_sha=commit_sha,
					headers=headers,
				)
				total_additions += additions
				total_deletions += deletions

		return len(repos), total_commits, total_additions, total_deletions

	def _fetch_org_repositories(self, headers: dict[str, str]) -> list[str]:
		"""Fetch organization repository names with pagination."""

		repository_names: list[str] = []
		page = 1
		while True:
			try:
				response = requests.get(
					f"https://api.github.com/orgs/{self._organization}/repos",
					headers=headers,
					params={"per_page": 100, "page": page},
					timeout=self._timeout_seconds,
				)
				response.raise_for_status()
				payload = response.json()
			except requests.RequestException:
				break

			if not payload:
				break

			repository_names.extend(
				repo.get("name", "") for repo in payload if repo.get("name")
			)
			page += 1

		return repository_names

	def _fetch_repo_commits(
		self,
		repo_name: str,
		since: str,
		until: str,
		headers: dict[str, str],
	) -> list[str]:
		"""Fetch commit SHAs for one repository in time range."""

		shas: list[str] = []
		page = 1
		while True:
			try:
				response = requests.get(
					f"https://api.github.com/repos/{self._organization}/{repo_name}/commits",
					headers=headers,
					params={
						"since": since,
						"until": until,
						"per_page": 100,
						"page": page,
					},
					timeout=self._timeout_seconds,
				)
				response.raise_for_status()
				payload = response.json()
			except requests.RequestException:
				break

			if not payload:
				break

			shas.extend(item.get("sha", "") for item in payload if item.get("sha"))
			page += 1

		return shas

	def _fetch_commit_stats(
		self,
		repo_name: str,
		commit_sha: str,
		headers: dict[str, str],
	) -> tuple[int, int]:
		"""Fetch additions and deletions for one commit SHA."""

		try:
			response = requests.get(
				f"https://api.github.com/repos/{self._organization}/{repo_name}/commits/{commit_sha}",
				headers=headers,
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			payload = response.json()
			stats = payload.get("stats", {})
			additions = int(stats.get("additions", 0))
			deletions = int(stats.get("deletions", 0))
			return additions, deletions
		except (requests.RequestException, ValueError, TypeError):
			return 0, 0

	def _headers(self) -> dict[str, str]:
		"""Build GitHub API request headers.

		Returns:
			Headers including authorization when api key is configured.
		"""

		headers = {"Accept": "application/vnd.github+json"}
		if self._api_key:
			headers["Authorization"] = f"Bearer {self._api_key}"
		return headers

