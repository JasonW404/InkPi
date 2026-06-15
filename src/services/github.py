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
		self._extra_repos = config.github.extra_repos
		self._commit_email = config.github.commit_email

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
		"""Fetch user commit counts across org repos, extra repos, and personal repos.

		Checks both authored commits (GitHub login match) and co-authored-by
		trailers in commit messages.

		Args:
			month_start: First day of month in UTC.
			repos: Organization repository names.

		Returns:
			Per-day commit counts from all sources.
		"""

		if not self._username:
			return []

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		commit_counter: Counter[date] = Counter()
		seen_shas: set[str] = set()

		all_repos: list[tuple[str, str]] = []
		if self._organization and repos:
			all_repos.extend((self._organization, r) for r in repos)
		for extra_repo in self._extra_repos:
			parts = extra_repo.split("/", 1)
			if len(parts) == 2:
				all_repos.append((parts[0], parts[1]))

		org_repos: list[tuple[str, str]] = []
		if self._organization and repos:
			org_repos.extend((self._organization, r) for r in repos)

		extra_repos: list[tuple[str, str]] = []
		for extra_repo in self._extra_repos:
			parts = extra_repo.split("/", 1)
			if len(parts) == 2:
				extra_repos.append((parts[0], parts[1]))

		for org, repo_name in org_repos:
			commits = self._api.fetch_repo_commits(
				organization=org,
				repo_name=repo_name,
				since=since,
				until=until,
			)
			self._collect_user_commit_days(commits, month_start, seen_shas, commit_counter)

		for org, repo_name in extra_repos:
			commits = self._fetch_commits_across_branches(org, repo_name, since, until)
			self._collect_user_commit_days(commits, month_start, seen_shas, commit_counter)

		return [
			GitHubContributionDay(day=day, commit_count=count)
			for day, count in sorted(commit_counter.items(), key=lambda item: item[0])
		]

	def _collect_user_commit_days(
		self,
		commits: list[dict[str, object]],
		month_start: date,
		seen_shas: set[str],
		commit_counter: Counter[date],
	) -> None:
		for commit in commits:
			sha = commit.get("sha")
			if not isinstance(sha, str) or not sha or sha in seen_shas:
				continue
			if not self._is_user_commit(commit):
				continue
			seen_shas.add(sha)
			commit_date_raw = ((commit.get("commit") or {}).get("author") or {}).get("date")
			if not isinstance(commit_date_raw, str) or not commit_date_raw:
				continue
			try:
				commit_day = datetime.fromisoformat(
					commit_date_raw.replace("Z", "+00:00")
				).date()
			except ValueError:
				continue
			if commit_day >= month_start:
				commit_counter[commit_day] += 1

	def _fetch_commits_across_branches(
		self,
		org: str,
		repo_name: str,
		since: str,
		until: str,
	) -> list[dict[str, object]]:
		branches_fn = getattr(self._api, "fetch_repo_branches", None)
		if not branches_fn:
			return self._api.fetch_repo_commits(
				organization=org, repo_name=repo_name, since=since, until=until,
			)

		branches = branches_fn(org, repo_name)
		if not branches:
			return []

		all_commits: list[dict[str, object]] = []
		seen: set[str] = set()
		for branch in branches:
			commits = self._api.fetch_repo_commits(
				organization=org, repo_name=repo_name,
				since=since, until=until, sha=branch,
			)
			for commit in commits:
				sha = commit.get("sha")
				if isinstance(sha, str) and sha and sha not in seen:
					seen.add(sha)
					all_commits.append(commit)
		return all_commits

	def _parse_search_commit_days(
		self,
		items: list[dict[str, object]],
		month_start: date,
	) -> list[GitHubContributionDay]:
		"""Deduplicate search results by SHA and aggregate per day."""

		seen_shas: set[str] = set()
		commit_counter: Counter[date] = Counter()

		for item in items:
			sha = item.get("sha")
			if not isinstance(sha, str) or not sha or sha in seen_shas:
				continue
			seen_shas.add(sha)

			commit_obj = item.get("commit")
			if not isinstance(commit_obj, dict):
				continue
			author_obj = commit_obj.get("author")
			if not isinstance(author_obj, dict):
				continue
			commit_date_raw = author_obj.get("date")
			if not isinstance(commit_date_raw, str) or not commit_date_raw:
				continue
			try:
				commit_day = datetime.fromisoformat(
					commit_date_raw.replace("Z", "+00:00")
				).date()
			except ValueError:
				continue
			if commit_day >= month_start:
				commit_counter[commit_day] += 1

		return [
			GitHubContributionDay(day=day, commit_count=count)
			for day, count in sorted(commit_counter.items(), key=lambda item: item[0])
		]

	def _fetch_user_monthly_commit_days_fallback(
		self,
		month_start: date,
		repos: list[str],
	) -> list[GitHubContributionDay]:
		"""Legacy PushEvents + org-repo fallback for adapters without search."""

		commit_counter: Counter[date] = Counter()

		org_repo_full_names: set[str] = set()
		if self._api.has_token() and repos and self._organization:
			org_repo_full_names = {
				f"{self._organization}/{repo}" for repo in repos
			}

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
		"""Fetch user monthly line changes from authored and co-authored commits."""

		if not (self._api.has_token() and self._username):
			return 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_lines = 0

		if self._organization and repos:
			for repo_name in repos:
				commits = self._api.fetch_repo_commits(
					organization=self._organization,
					repo_name=repo_name,
					since=since,
					until=until,
				)
				for item in commits:
					if not self._is_user_commit(item):
						continue
					sha = item.get("sha")
					if not isinstance(sha, str) or not sha:
						continue
					additions, deletions = self._fetch_commit_stats(
						repo_name=repo_name,
						commit_sha=sha,
					)
					total_lines += max(0, additions) + max(0, deletions)

		for extra_repo in self._extra_repos:
			parts = extra_repo.split("/", 1)
			if len(parts) != 2:
				continue
			extra_org, extra_name = parts
			commits = self._fetch_commits_across_branches(extra_org, extra_name, since, until)
			for item in commits:
				if not self._is_user_commit(item):
					continue
				sha = item.get("sha")
				if not isinstance(sha, str) or not sha:
					continue
				additions, deletions = self._fetch_cross_commit_stats(
					repo_full_name=extra_repo,
					commit_sha=sha,
				)
				total_lines += max(0, additions) + max(0, deletions)

		return total_lines

	def _fetch_org_monthly_stats(
		self,
		month_start: date,
		repos: list[str] | None = None,
	) -> tuple[int, int, int, int]:
		"""Fetch organization and extra-repo commit statistics.

		Args:
			month_start: First day of month in UTC.
			repos: Organization repository names.

		Returns:
			Tuple of repo count, commit count, additions, deletions.
		"""

		repository_list = repos if repos is not None else (
			self._fetch_org_repositories() if self._organization else []
		)

		if not repository_list and not self._extra_repos:
			return 0, 0, 0, 0

		since = datetime.combine(month_start, datetime.min.time(), tzinfo=UTC).isoformat()
		until = datetime.now(UTC).isoformat()
		total_commits = 0
		total_additions = 0
		total_deletions = 0

		if self._organization:
			for repo_name in repository_list:
				commits = self._api.fetch_repo_commits(
					organization=self._organization,
					repo_name=repo_name,
					since=since,
					until=until,
				)
				for commit in commits:
					if not self._is_user_commit(commit):
						continue
					total_commits += 1
					commit_sha = commit.get("sha")
					if not isinstance(commit_sha, str) or not commit_sha:
						continue
					additions, deletions = self._fetch_commit_stats(
						repo_name=repo_name,
						commit_sha=commit_sha,
					)
					total_additions += additions
					total_deletions += deletions

		for extra_repo in self._extra_repos:
			parts = extra_repo.split("/", 1)
			if len(parts) != 2:
				continue
			extra_org, extra_name = parts
			commits = self._fetch_commits_across_branches(extra_org, extra_name, since, until)
			for commit in commits:
				if not self._is_user_commit(commit):
					continue
				total_commits += 1
				commit_sha = commit.get("sha")
				if not isinstance(commit_sha, str) or not commit_sha:
					continue
				additions, deletions = self._fetch_cross_commit_stats(
					repo_full_name=extra_repo,
					commit_sha=commit_sha,
				)
				total_additions += additions
				total_deletions += deletions

		repo_count = len(repository_list) + len(self._extra_repos)
		return repo_count, total_commits, total_additions, total_deletions

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

	def _fetch_cross_commit_stats(
		self,
		repo_full_name: str,
		commit_sha: str,
	) -> tuple[int, int]:
		"""Fetch additions and deletions for a commit in any repository."""

		cross_fn = getattr(self._api, "fetch_cross_repo_commit_stats", None)
		if cross_fn:
			return cross_fn(repo_full_name, commit_sha)
		parts = repo_full_name.split("/", 1)
		if len(parts) == 2:
			return self._api.fetch_commit_stats(
				organization=parts[0],
				repo_name=parts[1],
				commit_sha=commit_sha,
			)
		return 0, 0

	def _is_user_commit(self, commit: dict[str, object]) -> bool:
		"""Check if commit is authored or co-authored by the configured user."""

		author = commit.get("author")
		if isinstance(author, dict) and author.get("login") == self._username:
			return True

		message = (commit.get("commit") or {}).get("message", "")
		if not isinstance(message, str):
			return False

		if "Co-authored-by:" not in message:
			return False

		emails_to_check = []
		if self._commit_email:
			emails_to_check.append(self._commit_email)
		if self._username:
			emails_to_check.append(f"{self._username}@users.noreply.github.com")

		for email in emails_to_check:
			if f"<{email}>" in message:
				return True

		return False

