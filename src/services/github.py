"""GitHub provider service for monthly contribution and organization stats."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
import logging
import time

from src.adapters.contracts import GitHubApiClient
from src.config import AppConfig
from src.domain.models import GitHubContributionDay, GitHubMonthlyStats


class GitHubService:
	"""Fetch GitHub dashboard metrics using authenticated API requests.

	Private repository data is available only when `api_key` is configured and
	has sufficient repository read permissions.
	"""

	def __init__(self, config: AppConfig, api_adapter: GitHubApiClient) -> None:
		"""Store GitHub source configuration.

		Args:
			config: Application configuration.
			api_adapter: GitHub API integration adapter.
		"""

		self._username = config.github.username
		self._organization = config.github.organization
		self._api = api_adapter
		self._logger = logging.getLogger(self.__class__.__name__)
		self._cached_monthly_stats: GitHubMonthlyStats | None = None
		self._cached_monthly_stats_monotonic: float = 0.0
		self._stats_cache_ttl_seconds = 3600

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
		repos = self._fetch_org_repositories() if self._organization else []

		if not self._api.has_token():
			self._logger.warning(
				"github_api_key_missing private_repo_data_will_not_be_included"
			)
		else:
			self._logger.info("github_api_key_present authenticated_requests_enabled")
		daily_commits = self._fetch_user_monthly_commit_days(
			month_start=month_start,
			repos=repos,
		)
		user_code_lines = self._fetch_user_monthly_code_lines(
			month_start=month_start,
			repos=repos,
		)
		repo_count, org_commit_count, additions, deletions = self._fetch_org_monthly_stats(
			month_start=month_start,
			repos=repos,
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

		# Determine which repos belong to the org so we can avoid double-counting.
		# Public PushEvents cover org repos too, so when org repo commits are
		# available (Source 2), skip org repos in public events (Source 1).
		org_repo_full_names: set[str] = set()
		if self._api.has_token() and repos and self._organization:
			org_repo_full_names = {
				f"{self._organization}/{repo}" for repo in repos
			}

		# Source 1: public events (works without token, but private events can be redacted).
		events = self._api.fetch_public_user_events(self._username)

		for event in events:
			if event.get("type") != "PushEvent":
				continue
			repo_info = event.get("repo")
			repo_full_name = (
				repo_info.get("name", "")
				if isinstance(repo_info, dict)
				else ""
			)
			if repo_full_name in org_repo_full_names:
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

		# Source 2: organization repo commits by author (authoritative for org repos).
		if org_repo_full_names:
			org_counter = self._fetch_user_org_commit_days(
				month_start=month_start,
				repos=repos,
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
	) -> int:
		"""Fetch user monthly line changes from authored commits in organization repos."""

		if not (self._api.has_token() and self._organization and self._username and repos):
			return 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_lines = 0

		for repo_name in repos:
			commits = self._api.fetch_repo_commits(
				organization=self._organization,
				repo_name=repo_name,
				since=since,
				until=until,
				author=self._username,
			)
			for item in commits:
				sha = item.get("sha")
				if not isinstance(sha, str) or not sha:
					continue
				additions, deletions = self._fetch_commit_stats(
					repo_name=repo_name,
					commit_sha=sha,
				)
				total_lines += max(0, additions) + max(0, deletions)

		return total_lines

	def _fetch_org_monthly_stats(
		self,
		month_start: date,
		repos: list[str] | None = None,
	) -> tuple[int, int, int, int]:
		"""Fetch organization repository and commit statistics.

		Args:
			month_start: First day of month in UTC.

		Returns:
			Tuple of repo count, commit count, additions, deletions.
		"""

		if not self._organization:
			return 0, 0, 0, 0

		repository_list = repos if repos is not None else self._fetch_org_repositories()
		if not repository_list:
			return 0, 0, 0, 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_commits = 0
		total_additions = 0
		total_deletions = 0

		for repo_name in repository_list:
			commits = self._api.fetch_repo_commits(
				organization=self._organization,
				repo_name=repo_name,
				since=since,
				until=until,
			)
			total_commits += len(commits)
			for commit in commits:
				commit_sha = commit.get("sha")
				if not isinstance(commit_sha, str) or not commit_sha:
					continue
				additions, deletions = self._fetch_commit_stats(
					repo_name=repo_name,
					commit_sha=commit_sha,
				)
				total_additions += additions
				total_deletions += deletions

		return len(repository_list), total_commits, total_additions, total_deletions

	def _fetch_user_org_commit_days(
		self,
		month_start: date,
		repos: list[str],
	) -> Counter[date]:
		"""Fetch per-day commit counts for configured user across organization repos."""

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		counter: Counter[date] = Counter()

		for repo_name in repos:
			commits = self._api.fetch_repo_commits(
				organization=self._organization,
				repo_name=repo_name,
				since=since,
				until=until,
				author=self._username,
			)

			for item in commits:
				commit_date_raw = ((item.get("commit") or {}).get("author") or {}).get("date")
				if not isinstance(commit_date_raw, str) or not commit_date_raw:
					continue
				try:
					commit_day = datetime.fromisoformat(
						commit_date_raw.replace("Z", "+00:00")
					).date()
				except ValueError:
					continue
				if commit_day >= month_start:
					counter[commit_day] += 1

		return counter

	def _fetch_org_repositories(self) -> list[str]:
		"""Fetch organization repository names with pagination."""

		repository_names, forbidden = self._api.fetch_org_repositories(self._organization)

		if forbidden:
			self._logger.warning(
				"github_org_repo_access_denied status=%s org=%s",
				403,
				self._organization,
			)

		if forbidden and self._api.has_token():
			# Fallback to user-style endpoint when org endpoint is blocked.
			userstyle_repos = self._api.fetch_org_repositories_from_user_endpoint(self._organization)
			if userstyle_repos:
				self._logger.info(
					"github_repo_fallback_used source=user_endpoint count=%s org=%s",
					len(userstyle_repos),
					self._organization,
				)
				return userstyle_repos

			fallback = self._api.fetch_accessible_org_repositories(self._organization)
			if fallback:
				self._logger.info(
					"github_repo_fallback_used source=user_repos count=%s org=%s",
					len(fallback),
					self._organization,
				)
				return fallback

		return repository_names

	def _fetch_commit_stats(
		self,
		repo_name: str,
		commit_sha: str,
	) -> tuple[int, int]:
		"""Fetch additions and deletions for one commit SHA."""

		return self._api.fetch_commit_stats(
			organization=self._organization,
			repo_name=repo_name,
			commit_sha=commit_sha,
		)

