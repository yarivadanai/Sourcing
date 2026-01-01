"""Hackathon winners data source."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class HackathonSource(BaseSource):
    """Collect leads from hackathon winners."""

    def __init__(self):
        super().__init__("hackathon")
        self.hackathons = self._get_hackathon_config()

    def _get_hackathon_config(self) -> Dict:
        """Configuration for hackathon platforms and events."""
        return {
            'devpost': {
                'name': 'Devpost',
                'base_url': 'https://devpost.com',
                'api_url': 'https://devpost.com/api/hackathons',
                'focus': 'AI hackathons',
                'prestige': 8,
            },
            'mlh': {
                'name': 'Major League Hacking',
                'base_url': 'https://mlh.io',
                'events_url': 'https://mlh.io/seasons/2024/events',
                'focus': 'Student hackathons',
                'prestige': 7,
            },
            'junction': {
                'name': 'Junction',
                'base_url': 'https://www.junction.fi',
                'focus': 'Europe largest hackathon',
                'prestige': 9,
            },
            'hackzurich': {
                'name': 'HackZurich',
                'base_url': 'https://hackzurich.com',
                'focus': 'Switzerland',
                'prestige': 8,
            },
            'eth_hackathon': {
                'name': 'ETH Hackathon',
                'base_url': 'https://www.eth-hack.com',
                'focus': 'Switzerland',
                'prestige': 8,
            },
        }

    def collect(self) -> List[RawLead]:
        """Collect winners from all hackathon sources."""
        self.logger.info("Collecting hackathon winners")

        leads = []

        # Collect from Devpost
        try:
            devpost_leads = self._collect_devpost()
            leads.extend(devpost_leads)
            self.logger.info(f"Devpost: {len(devpost_leads)} leads")
        except Exception as e:
            self.logger.error(f"Failed to collect from Devpost: {e}")

        # Collect from MLH
        try:
            mlh_leads = self._collect_mlh()
            leads.extend(mlh_leads)
            self.logger.info(f"MLH: {len(mlh_leads)} leads")
        except Exception as e:
            self.logger.error(f"Failed to collect from MLH: {e}")

        self.log_result(len(leads))
        return leads

    def _collect_devpost(self) -> List[RawLead]:
        """
        Collect AI hackathon winners from Devpost.

        Devpost has an unofficial API that returns JSON data.
        """
        leads = []

        try:
            # Get recent AI hackathons
            url = "https://devpost.com/api/hackathons"
            params = {
                'challenge_type[]': 'online',
                'status': 'ended',
                'themes[]': 'Artificial Intelligence',
                'page': 1,
                'per_page': 20
            }

            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                return leads

            data = response.json()
            hackathons = data.get('hackathons', [])

            for hackathon in hackathons:
                # Check if recent (last 6 months)
                end_date_str = hackathon.get('submission_period_ends_at')
                if not end_date_str:
                    continue

                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    months_old = (datetime.now(end_date.tzinfo) - end_date).days // 30

                    if months_old > 6:
                        continue  # Skip old hackathons
                except Exception:
                    continue

                # Get winners for this hackathon
                hackathon_url = hackathon.get('url')
                if hackathon_url:
                    winners = self._get_devpost_winners(hackathon_url, hackathon.get('title'), months_old)
                    leads.extend(winners)

        except Exception as e:
            self.logger.error(f"Failed to collect from Devpost API: {e}")

        return leads

    def _get_devpost_winners(self, hackathon_url: str, hackathon_name: str, months_old: int) -> List[RawLead]:
        """Scrape winners from a specific Devpost hackathon."""
        leads = []

        try:
            # Winners are usually at /project-gallery with winner filter
            winners_url = f"{hackathon_url}/project-gallery"

            response = requests.get(winners_url, timeout=30)
            if response.status_code != 200:
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find winning projects
            winner_projects = soup.find_all('div', class_='software-entry')

            for project in winner_projects[:10]:  # Top 10 winners
                try:
                    # Check if it's actually a winner
                    winner_badge = project.find('span', class_='winner')
                    if not winner_badge:
                        continue

                    # Extract project details
                    title_elem = project.find('h5', class_='software-entry-name')
                    project_name = title_elem.get_text().strip() if title_elem else ''

                    # Extract description
                    desc_elem = project.find('p', class_='software-entry-description')
                    description = desc_elem.get_text().strip() if desc_elem else ''

                    # Filter for AI projects
                    if not self._is_ai_related(description + ' ' + project_name):
                        continue

                    # Extract team members
                    members_section = project.find('div', class_='software-entry-collaborators')
                    if not members_section:
                        continue

                    member_links = members_section.find_all('a')

                    for member_link in member_links:
                        member_name = member_link.get('title') or member_link.get_text().strip()
                        member_url = member_link.get('href')

                        if member_name:
                            lead = RawLead(
                                name=member_name,
                                source='hackathon',
                                source_url=member_url or hackathon_url,
                                raw_data={
                                    'hackathon_name': hackathon_name,
                                    'project_name': project_name,
                                    'prize': winner_badge.get_text().strip(),
                                    'project_description': description,
                                    'months_old': months_old,
                                    'hackathon_platform': 'Devpost',
                                }
                            )

                            leads.append(lead)

                except Exception as e:
                    self.logger.warning(f"Failed to process project: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scrape winners from {hackathon_url}: {e}")

        return leads

    def _collect_mlh(self) -> List[RawLead]:
        """
        Collect from Major League Hacking events.

        Note: MLH requires scraping individual event pages.
        """
        leads = []

        try:
            # Get MLH events page
            url = "https://mlh.io/seasons/2024/events"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find European events
            event_items = soup.find_all('div', class_='event')

            for event in event_items[:20]:  # Check recent 20 events
                try:
                    # Check if European location
                    location_elem = event.find('span', class_='event-location')
                    if not location_elem:
                        continue

                    location = location_elem.get_text().strip()

                    # Filter for European locations
                    european_keywords = [
                        'uk', 'london', 'berlin', 'germany', 'paris', 'france',
                        'zurich', 'switzerland', 'amsterdam', 'netherlands',
                        'stockholm', 'sweden', 'europe'
                    ]

                    if not any(keyword in location.lower() for keyword in european_keywords):
                        continue

                    # Extract event details
                    name_elem = event.find('h3', class_='event-name')
                    event_name = name_elem.get_text().strip() if name_elem else ''

                    # For MLH, winners are typically announced on social media
                    # This would require additional scraping of event websites
                    # Placeholder for now

                except Exception as e:
                    self.logger.warning(f"Failed to process MLH event: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to collect from MLH: {e}")

        return leads

    def _is_ai_related(self, text: str) -> bool:
        """Check if project is AI-related."""
        if not text:
            return False

        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural', 'nlp', 'computer vision', 'llm', 'large language model',
            'gpt', 'chatbot', 'generative', 'model', 'prediction', 'automation',
            'robotics', 'autonomous'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ai_keywords)
