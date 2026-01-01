"""Twitter/X academic monitoring source."""

import requests
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class TwitterSource(BaseSource):
    """Monitor Twitter/X for academic AI community activity."""

    def __init__(self):
        super().__init__("twitter")
        self.bearer_token = settings.twitter_bearer_token
        self.api_base = "https://api.twitter.com/2"

    def collect(self) -> List[RawLead]:
        """
        Collect from Twitter/X academic AI community.

        Monitors:
        - AI researchers announcing papers
        - "Building in public" threads
        - New project/startup announcements
        - Conference participation
        """
        self.logger.info("Collecting from Twitter/X academic community")

        if not self.bearer_token:
            self.logger.warning("Twitter Bearer Token not configured, skipping Twitter source")
            return []

        leads = []

        # Search for announcement tweets
        try:
            # Keyword searches
            keywords = [
                '"new paper" AI machine learning',
                '"just released" model',
                '"building" startup AI',
                '"founding" deep tech',
                'stealth mode AI',
            ]

            for keyword in keywords:
                keyword_leads = self._search_tweets(keyword)
                leads.extend(keyword_leads)

        except Exception as e:
            self.logger.error(f"Failed to collect from Twitter: {e}")

        self.log_result(len(leads))
        return leads

    def _search_tweets(self, query: str, max_results: int = 100) -> List[RawLead]:
        """
        Search recent tweets using Twitter API v2.

        Requires Twitter API Essential access (free tier) or higher.
        """
        leads = []

        try:
            url = f"{self.api_base}/tweets/search/recent"

            # Add European location filter
            location_filter = ' (Europe OR UK OR Switzerland OR Germany OR France OR Sweden)'
            full_query = query + location_filter

            params = {
                'query': full_query,
                'max_results': min(max_results, 100),  # API limit
                'tweet.fields': 'created_at,author_id,text',
                'user.fields': 'name,username,description,location',
                'expansions': 'author_id'
            }

            headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # Extract users from tweets
                users = {user['id']: user for user in data.get('includes', {}).get('users', [])}

                for tweet in data.get('data', []):
                    author_id = tweet.get('author_id')
                    user = users.get(author_id)

                    if not user:
                        continue

                    # Filter for European location
                    location = user.get('location', '')
                    if not self.is_european_location(location, settings.target_cities):
                        continue

                    # Extract user info
                    name = user.get('name')
                    username = user.get('username')
                    bio = user.get('description', '')

                    # Check if academic/researcher
                    if not self._is_academic_profile(bio):
                        continue

                    lead = RawLead(
                        name=name or username,
                        source='twitter',
                        twitter_handle=username,
                        location=location,
                        source_url=f"https://twitter.com/{username}",
                        raw_data={
                            'twitter_bio': bio,
                            'tweet_text': tweet.get('text'),
                            'building_in_public_tweets': 1,  # Indicator
                            'is_academic': True,
                        }
                    )

                    leads.append(lead)

            elif response.status_code == 429:
                self.logger.warning("Twitter API rate limit hit")
            else:
                self.logger.warning(f"Twitter API error {response.status_code}: {response.text}")

        except Exception as e:
            self.logger.error(f"Failed to search tweets: {e}")

        return leads

    def _is_academic_profile(self, bio: str) -> bool:
        """Check if Twitter bio indicates academic/researcher."""
        if not bio:
            return False

        academic_keywords = [
            'phd', 'researcher', 'professor', 'postdoc', 'graduate student',
            'research scientist', 'faculty', 'university', 'institute',
            'eth', 'epfl', 'oxford', 'cambridge', 'imperial',
            'machine learning', 'deep learning', 'ai researcher'
        ]

        bio_lower = bio.lower()
        return any(keyword in bio_lower for keyword in academic_keywords)

    def monitor_lists(self, list_ids: List[str]) -> List[RawLead]:
        """
        Monitor specific Twitter lists for activity.

        Example lists:
        - "AI Researchers Europe"
        - "Deep Tech Founders"
        - "Academic AI Twitter"
        """
        leads = []

        for list_id in list_ids:
            try:
                # Get recent tweets from list
                url = f"{self.api_base}/lists/{list_id}/tweets"

                params = {
                    'max_results': 100,
                    'tweet.fields': 'created_at,author_id',
                    'user.fields': 'name,username,location',
                    'expansions': 'author_id'
                }

                headers = {
                    'Authorization': f'Bearer {self.bearer_token}'
                }

                response = requests.get(url, params=params, headers=headers, timeout=30)

                if response.status_code == 200:
                    # Process tweets similar to search
                    # Extract active users
                    pass

            except Exception as e:
                self.logger.error(f"Failed to monitor list {list_id}: {e}")

        return leads
