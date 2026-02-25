"""GitHub provider service for monthly contribution and organization stats."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
import logging
import time

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
		self._cached_monthly_stats: GitHubMonthlyStats | None = None
		self._cached_monthly_stats_monotonic: float = 0.0
		self._stats_cache_ttl_seconds = 300

	def get_monthly_stats(self) -> GitHubMonthlyStats:
		"""Collect current-month GitHub metrics.

		Returns:
			Monthly GitHub statistics for dashboard rendering.
		"""

		now_mono = time.monotonic()
		if (
			self._cached_monthly_stats is not None
			and now_mono - self._cached_monthly_stats_monotonic < self._stats_cache_ttl_seconds
		):
			return self._cached_monthly_stats

		now = datetime.now(UTC)
		month_start = date(year=now.year, month=now.month, day=1)
		month_label = month_start.strftime("%Y-%m")
		headers = self._headers()
		repos = self._fetch_org_repositories(headers) if self._organization else []

		if not self._api_key:
			self._logger.warning(
				"github_api_key_missing private_repo_data_will_not_be_included"
			)
		else:
			self._logger.info("github_api_key_present authenticated_requests_enabled")
		daily_commits = self._fetch_user_monthly_commit_days(
			month_start=month_start,
			repos=repos,
			headers=headers,
		)
		user_code_lines = self._fetch_user_monthly_code_lines(
			month_start=month_start,
			repos=repos,
			headers=headers,
		)
		repo_count, org_commit_count, additions, deletions = self._fetch_org_monthly_stats(
			month_start=month_start,
			repos=repos,
			headers=headers,
		)
		org_code_lines = max(0, additions) + max(0, deletions)

		stats = GitHubMonthlyStats(
			month=month_label,
			contributions=daily_commits,
			user_monthly_code_lines=user_code_lines,
			organization_repo_count=repo_count,
			organization_monthly_commit_count=org_commit_count,
			organization_monthly_code_lines=org_code_lines,
			organization_additions=additions,
			organization_deletions=deletions,
		)
		self._cached_monthly_stats = stats
		self._cached_monthly_stats_monotonic = now_mono
		return stats

	def _fetch_user_monthly_commit_days(
		self,
		month_start: date,
		repos: list[str],
		headers: dict[str, str],
	) -> list[GitHubContributionDay]:
		"""Fetch user push-event commit counts for current month.

		Args:
			month_start: First day of month in UTC.

		Returns:
			Per-day commit counts from available events.
		"""

		if not self._username:
			return []

		commit_counter: Counter[date] = Counter()

		# Source 1: public events (works without token, but private events can be redacted).
		try:
			response = requests.get(
				f"https://api.github.com/users/{self._username}/events/public",
				headers=headers,
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			events = response.json()
		except requests.RequestException:
			events = []

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
			if commit_count > 0:
				commit_counter[event_date] += commit_count

		# Source 2: organization repo commits by author (captures private repo commits).
		if self._api_key and repos and self._organization:
			org_counter = self._fetch_user_org_commit_days(
				month_start=month_start,
				repos=repos,
				headers=headers,
			)
			for day, count in org_counter.items():
				commit_counter[day] += count

		return [
			GitHubContributionDay(day=day, commit_count=count)
			for day, count in sorted(commit_counter.items(), key=lambda item: item[0])
		]

	def _fetch_user_monthly_code_lines(
		self,
		month_start: date,
		repos: list[str],
		headers: dict[str, str],
	) -> int:
		"""Fetch user monthly line changes from authored commits in organization repos."""

		if not (self._api_key and self._organization and self._username and repos):
			return 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_lines = 0

		for repo_name in repos:
			page = 1
			while True:
				try:
					response = requests.get(
						f"https://api.github.com/repos/{self._organization}/{repo_name}/commits",
						headers=headers,
						params={
							"since": since,
							"until": until,
							"author": self._username,
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

				for item in payload:
					sha = item.get("sha")
					if not sha:
						continue
					additions, deletions = self._fetch_commit_stats(
						repo_name=repo_name,
						commit_sha=sha,
						headers=headers,
					)
					total_lines += max(0, additions) + max(0, deletions)

				page += 1

		return total_lines

	def _fetch_org_monthly_stats(
		self,
		month_start: date,
		repos: list[str] | None = None,
		headers: dict[str, str] | None = None,
	) -> tuple[int, int, int, int]:
		"""Fetch organization repository and commit statistics.

		Args:
			month_start: First day of month in UTC.

		Returns:
			Tuple of repo count, commit count, additions, deletions.
		"""

		if not self._organization:
			return 0, 0, 0, 0

		request_headers = headers if headers is not None else self._headers()
		repository_list = repos if repos is not None else self._fetch_org_repositories(request_headers)
		if not repository_list:
			return 0, 0, 0, 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_commits = 0
		total_additions = 0
		total_deletions = 0

		for repo_name in repository_list:
			commits = self._fetch_repo_commits(
				repo_name,
				since=since,
				until=until,
				headers=request_headers,
			)
			total_commits += len(commits)
			for commit_sha in commits:
				additions, deletions = self._fetch_commit_stats(
					repo_name=repo_name,
					commit_sha=commit_sha,
					headers=request_headers,
				)
				total_additions += additions
				total_deletions += deletions

		return len(repository_list), total_commits, total_additions, total_deletions

	def _fetch_user_org_commit_days(
		self,
		month_start: date,
		repos: list[str],
		headers: dict[str, str],
	) -> Counter[date]:
		"""Fetch per-day commit counts for configured user across organization repos."""

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		counter: Counter[date] = Counter()

		for repo_name in repos:
			page = 1
			while True:
				try:
					response = requests.get(
						f"https://api.github.com/repos/{self._organization}/{repo_name}/commits",
						headers=headers,
						params={
							"since": since,
							"until": until,
							"author": self._username,
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

				for item in payload:
					commit_date_raw = (
						(item.get("commit") or {}).get("author") or {}
					).get("date")
					if not commit_date_raw:
						continue
					try:
						commit_day = datetime.fromisoformat(
							commit_date_raw.replace("Z", "+00:00")
						).date()
					except ValueError:
						continue
					if commit_day >= month_start:
						counter[commit_day] += 1

				page += 1

		return counter

	def _fetch_org_repositories(self, headers: dict[str, str]) -> list[str]:
		"""Fetch organization repository names with pagination."""

		repository_names: list[str] = []
		page = 1
		forbidden = False
		while True:
			try:
				response = requests.get(
					f"https://api.github.com/orgs/{self._organization}/repos",
					headers=headers,
					params={"type": "all", "per_page": 100, "page": page},
					timeout=self._timeout_seconds,
				)
				if response.status_code in {401, 403}:
					self._logger.warning(
						"github_org_repo_access_denied status=%s org=%s",
						response.status_code,
						self._organization,
					)
					forbidden = True
					break
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

		if forbidden and headers.get("Authorization"):
			# Fallback to user-style endpoint when org endpoint is blocked.
			userstyle_repos = self._fetch_org_repositories_from_user_endpoint(headers)
			if userstyle_repos:
				self._logger.info(
					"github_repo_fallback_used source=user_endpoint count=%s org=%s",
					len(userstyle_repos),
					self._organization,
				)
				return userstyle_repos

			fallback = self._fetch_accessible_org_repositories(headers)
			if fallback:
				self._logger.info(
					"github_repo_fallback_used source=user_repos count=%s org=%s",
					len(fallback),
					self._organization,
				)
				return fallback

		return repository_names

	def _fetch_org_repositories_from_user_endpoint(self, headers: dict[str, str]) -> list[str]:
		"""Fallback: fetch organization repositories using /users/{org}/repos."""

		repository_names: list[str] = []
		page = 1
		while True:
			try:
				response = requests.get(
					f"https://api.github.com/users/{self._organization}/repos",
					headers=headers,
					params={"type": "all", "per_page": 100, "page": page},
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

	def _fetch_accessible_org_repositories(self, headers: dict[str, str]) -> list[str]:
		"""Fallback: fetch accessible repos from /user/repos and filter by owner."""

		repository_names: list[str] = []
		page = 1
		while True:
			try:
				response = requests.get(
					"https://api.github.com/user/repos",
					headers=headers,
					params={
						"visibility": "all",
						"affiliation": "owner,organization_member,collaborator",
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

			for repo in payload:
				owner = (repo.get("owner") or {}).get("login", "")
				name = repo.get("name", "")
				if owner == self._organization and name:
					repository_names.append(name)

			page += 1

		# Deduplicate while preserving order.
		seen: set[str] = set()
		unique: list[str] = []
		for name in repository_names:
			if name in seen:
				continue
			seen.add(name)
			unique.append(name)
		return unique

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

