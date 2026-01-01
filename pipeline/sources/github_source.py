"""GitHub trending repositories and contributors data source."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class GitHubSource(BaseSource):
    """Collect leads from GitHub trending and AI repositories."""

    def __init__(self, github_token: Optional[str] = None):
        super().__init__("github")
        self.github_token = github_token or settings.github_token
        self.headers = {}
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'

    def collect(self) -> List[RawLead]:
        """Collect leads from GitHub trending and AI repos."""
        self.logger.info("Collecting GitHub contributors")

        leads = []

        # Collect from trending repos
        trending_leads = self._collect_trending_repos(['python', 'rust', 'cpp'])
        leads.extend(trending_leads)

        # Collect from AI topic search
        topic_leads = self._collect_by_topics(settings.ai_topics[:5])  # Top 5 AI topics
        leads.extend(topic_leads)

        self.log_result(len(leads))
        return leads

    def _collect_trending_repos(self, languages: List[str]) -> List[RawLead]:
        """Scrape GitHub trending page (no official API)."""
        leads = []

        for language in languages:
            try:
                url = f"https://github.com/trending/{language}?since=weekly"
                response = requests.get(url, timeout=30)

                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch trending for {language}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find trending repos
                repo_articles = soup.find_all('article', class_='Box-row')

                for article in repo_articles[:20]:  # Top 20 per language
                    try:
                        # Extract repo owner/name
                        repo_link = article.find('h2').find('a')
                        if not repo_link:
                            continue

                        full_name = repo_link['href'].strip('/')
                        owner, repo_name = full_name.split('/')

                        # Get owner profile
                        owner_lead = self._get_user_profile(owner, repo_name, language)
                        if owner_lead:
                            leads.append(owner_lead)

                        # Get top contributors
                        contributors = self._get_repo_contributors(owner, repo_name, limit=3)
                        leads.extend(contributors)

                    except Exception as e:
                        self.logger.warning(f"Failed to process trending repo: {e}")
                        continue

            except Exception as e:
                self.logger.error(f"Failed to collect trending for {language}: {e}")

        return leads

    def _collect_by_topics(self, topics: List[str]) -> List[RawLead]:
        """Search for repos by AI topics and European locations."""
        leads = []

        for topic in topics:
            for location in ['zurich', 'london', 'berlin', 'paris', 'stockholm']:
                try:
                    # GitHub search API
                    query = f"topic:{topic} location:{location}"
                    url = "https://api.github.com/search/repositories"

                    response = requests.get(
                        url,
                        headers=self.headers,
                        params={
                            'q': query,
                            'sort': 'stars',
                            'order': 'desc',
                            'per_page': 10
                        },
                        timeout=30
                    )

                    if response.status_code != 200:
                        continue

                    repos = response.json().get('items', [])

                    for repo in repos:
                        owner = repo['owner']['login']
                        repo_name = repo['name']

                        # Get owner profile
                        owner_lead = self._get_user_profile(
                            owner,
                            repo_name,
                            topic,
                            stars=repo.get('stargazers_count', 0)
                        )
                        if owner_lead:
                            leads.append(owner_lead)

                except Exception as e:
                    self.logger.warning(f"Failed to search topic {topic} in {location}: {e}")

        return leads

    def _get_user_profile(
        self,
        username: str,
        repo_name: Optional[str] = None,
        topic: Optional[str] = None,
        stars: int = 0
    ) -> Optional[RawLead]:
        """Fetch detailed user profile from GitHub API."""
        try:
            url = f"https://api.github.com/users/{username}"
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code != 200:
                return None

            user = response.json()

            # Check if European location
            location = user.get('location', '')
            if not self.is_european_location(location, settings.target_cities):
                return None

            # Get recent activity
            recent_commits = self._count_recent_commits(username)

            lead = RawLead(
                name=user.get('name') or username,
                source='github',
                github_profile=user.get('html_url'),
                twitter_handle=user.get('twitter_username'),
                location=location,
                company_name=user.get('company'),
                source_url=user.get('html_url'),
                raw_data={
                    'username': username,
                    'followers': user.get('followers', 0),
                    'public_repos': user.get('public_repos', 0),
                    'bio': user.get('bio', ''),
                    'blog': user.get('blog', ''),
                    'email': user.get('email'),
                    'is_european': True,
                    'trending_repo': repo_name is not None,
                    'repo_name': repo_name,
                    'topics': [topic] if topic else [],
                    'recent_commits': recent_commits > 0,
                    'github_commits_last_30d': recent_commits,
                    'repo_stars': stars,
                }
            )

            return lead

        except Exception as e:
            self.logger.warning(f"Failed to get profile for {username}: {e}")
            return None

    def _get_repo_contributors(self, owner: str, repo: str, limit: int = 5) -> List[RawLead]:
        """Get top contributors for a repository."""
        leads = []

        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
            response = requests.get(
                url,
                headers=self.headers,
                params={'per_page': limit},
                timeout=30
            )

            if response.status_code != 200:
                return leads

            contributors = response.json()

            for contrib in contributors:
                username = contrib.get('login')
                contributions = contrib.get('contributions', 0)

                # Get full profile
                lead = self._get_user_profile(username, repo_name=repo)
                if lead:
                    # Add contribution count to raw data
                    lead.raw_data['contributions'] = contributions
                    leads.append(lead)

        except Exception as e:
            self.logger.warning(f"Failed to get contributors for {owner}/{repo}: {e}")

        return leads

    def _count_recent_commits(self, username: str, days: int = 30) -> int:
        """Count commits by user in last N days."""
        try:
            # Search for recent commits by user
            since_date = (datetime.now() - timedelta(days=days)).isoformat()

            url = "https://api.github.com/search/commits"
            response = requests.get(
                url,
                headers={**self.headers, 'Accept': 'application/vnd.github.cloak-preview'},
                params={
                    'q': f'author:{username} author-date:>{since_date}',
                    'per_page': 1
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get('total_count', 0)

        except Exception as e:
            self.logger.debug(f"Failed to count commits for {username}: {e}")

        return 0


from datetime import timedelta
