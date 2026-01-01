"""Technical blogs monitoring source (Medium, Substack)."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class BlogSource(BaseSource):
    """Monitor technical blogs for AI/ML content from European authors."""

    def __init__(self):
        super().__init__("blog")

    def collect(self) -> List[RawLead]:
        """
        Collect from technical blogs.

        Monitors:
        - Medium AI tags
        - Substack AI newsletters
        - Personal blogs (discovered via other sources)
        """
        self.logger.info("Collecting from technical blogs")

        leads = []

        # Collect from Medium
        try:
            medium_leads = self._collect_medium()
            leads.extend(medium_leads)
            self.logger.info(f"Medium: {len(medium_leads)} leads")
        except Exception as e:
            self.logger.error(f"Failed to collect from Medium: {e}")

        # Collect from Substack
        try:
            substack_leads = self._collect_substack()
            leads.extend(substack_leads)
            self.logger.info(f"Substack: {len(substack_leads)} leads")
        except Exception as e:
            self.logger.error(f"Failed to collect from Substack: {e}")

        self.log_result(len(leads))
        return leads

    def _collect_medium(self) -> List[RawLead]:
        """
        Collect AI authors from Medium.

        Medium has limited public API, so we scrape tag pages.
        """
        leads = []

        ai_tags = [
            'machine-learning',
            'deep-learning',
            'artificial-intelligence',
            'llm',
            'computer-vision'
        ]

        for tag in ai_tags:
            try:
                # Medium tag page
                url = f"https://medium.com/tag/{tag}"

                response = requests.get(url, timeout=30)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find recent articles
                # Note: Medium's structure changes frequently
                # This is a template selector
                articles = soup.find_all('article')[:20]

                for article in articles:
                    try:
                        # Extract author info
                        author_link = article.find('a', {'data-action': 'show-user-card'})
                        if not author_link:
                            continue

                        author_name = author_link.get_text().strip()
                        author_url = author_link.get('href')

                        # Get author profile to check location
                        author_lead = self._get_medium_author(author_name, author_url)
                        if author_lead:
                            leads.append(author_lead)

                    except Exception as e:
                        self.logger.debug(f"Failed to process article: {e}")
                        continue

            except Exception as e:
                self.logger.warning(f"Failed to scrape Medium tag {tag}: {e}")

        return leads

    def _get_medium_author(self, name: str, profile_url: str) -> Optional[RawLead]:
        """Get Medium author profile and check if European."""
        try:
            if not profile_url:
                return None

            # Ensure full URL
            if not profile_url.startswith('http'):
                profile_url = f"https://medium.com{profile_url}"

            response = requests.get(profile_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract bio/description
            bio_elem = soup.find('p', class_='bio')
            bio = bio_elem.get_text().strip() if bio_elem else ''

            # Check for location in bio or profile
            # Medium doesn't have explicit location field
            # Look for European keywords in bio

            european_indicators = [
                'zurich', 'switzerland', 'london', 'uk', 'berlin', 'germany',
                'paris', 'france', 'amsterdam', 'stockholm', 'europe',
                'eth', 'epfl', 'oxford', 'cambridge', 'imperial'
            ]

            bio_lower = bio.lower()
            is_european = any(indicator in bio_lower for indicator in european_indicators)

            if not is_european:
                return None

            # Check if academic/technical
            if not self._is_technical_profile(bio):
                return None

            lead = RawLead(
                name=name,
                source='blog',
                source_url=profile_url,
                raw_data={
                    'platform': 'Medium',
                    'bio': bio[:500],
                    'profile_url': profile_url,
                    'content_focus': 'AI/ML',
                }
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Failed to get Medium author profile: {e}")
            return None

    def _collect_substack(self) -> List[RawLead]:
        """
        Collect AI newsletter authors from Substack.

        Substack discovery is typically through:
        - Substack Discover (browse AI category)
        - Direct newsletter URLs
        """
        leads = []

        try:
            # Substack doesn't have a public API
            # Would need to:
            # 1. Browse Substack Discover for AI/ML newsletters
            # 2. Extract author information
            # 3. Check for European connection

            # Placeholder for Substack discovery
            # In practice, you might maintain a curated list of known AI Substacks

            known_ai_substacks = [
                # Examples - would need actual discovery
                # 'https://newsletter.substack.com'
            ]

            for substack_url in known_ai_substacks:
                author_lead = self._get_substack_author(substack_url)
                if author_lead:
                    leads.append(author_lead)

        except Exception as e:
            self.logger.error(f"Failed to collect from Substack: {e}")

        return leads

    def _get_substack_author(self, substack_url: str) -> Optional[RawLead]:
        """Get Substack newsletter author information."""
        try:
            response = requests.get(substack_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract author name
            author_elem = soup.find('a', class_='author-name')
            author_name = author_elem.get_text().strip() if author_elem else None

            if not author_name:
                return None

            # Extract description
            desc_elem = soup.find('div', class_='publication-description')
            description = desc_elem.get_text().strip() if desc_elem else ''

            # Check for European connection
            if not self.is_european_location(description, settings.target_cities):
                return None

            lead = RawLead(
                name=author_name,
                source='blog',
                source_url=substack_url,
                raw_data={
                    'platform': 'Substack',
                    'newsletter_description': description[:500],
                    'content_focus': 'AI/ML',
                }
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Failed to get Substack author: {e}")
            return None

    def _is_technical_profile(self, bio: str) -> bool:
        """Check if bio indicates technical/AI background."""
        if not bio:
            return False

        technical_keywords = [
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'researcher', 'engineer', 'developer', 'phd', 'data scientist',
            'neural network', 'computer science'
        ]

        bio_lower = bio.lower()
        return any(keyword in bio_lower for keyword in technical_keywords)
