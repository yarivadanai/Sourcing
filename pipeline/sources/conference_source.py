"""AI Conference speakers and presenters data source."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class ConferenceSource(BaseSource):
    """Collect leads from major AI conference speakers and presenters."""

    def __init__(self):
        super().__init__("conference")
        self.conferences = self._get_conference_config()

    def _get_conference_config(self) -> Dict:
        """Configuration for major AI conferences."""
        current_year = datetime.now().year

        return {
            'neurips': {
                'name': 'NeurIPS',
                'url': f'https://neurips.cc/Conferences/{current_year}/Schedule',
                'prestige': 10,
                'focus': ['oral', 'spotlight', 'workshop organizer'],
            },
            'icml': {
                'name': 'ICML',
                'url': f'https://icml.cc/Conferences/{current_year}/Schedule',
                'prestige': 10,
                'focus': ['oral', 'spotlight'],
            },
            'iclr': {
                'name': 'ICLR',
                'url': f'https://iclr.cc/Conferences/{current_year}/Schedule',
                'prestige': 10,
                'focus': ['oral', 'spotlight'],
            },
            'cvpr': {
                'name': 'CVPR',
                'url': f'https://cvpr{current_year}.thecvf.com/program/accepted-papers',
                'prestige': 10,
                'focus': ['oral', 'best paper'],
            },
            'eccv': {
                'name': 'ECCV',
                'url': f'https://eccv{current_year}.ecva.net/program/accepted-papers',
                'prestige': 10,
                'focus': ['oral'],
            },
            'emnlp': {
                'name': 'EMNLP',
                'url': f'https://{current_year}.emnlp.org/program/accepted_main_conference/',
                'prestige': 9,
                'focus': ['oral', 'best paper'],
            },
            'acl': {
                'name': 'ACL',
                'url': f'https://{current_year}.aclweb.org/program/accepted/',
                'prestige': 9,
                'focus': ['oral'],
            },
            # European-specific conferences
            'ecai': {
                'name': 'ECAI',
                'url': f'https://ecai{current_year}.eu/programme/accepted-papers',
                'prestige': 8,
                'focus': ['oral', 'best paper'],
            },
        }

    def collect(self) -> List[RawLead]:
        """Collect speakers from major AI conferences."""
        self.logger.info("Collecting conference speakers")

        leads = []

        for conf_key, conf_config in self.conferences.items():
            try:
                conf_leads = self._collect_conference(conf_key, conf_config)
                leads.extend(conf_leads)
                self.logger.info(f"{conf_config['name']}: {len(conf_leads)} leads")
            except Exception as e:
                self.logger.error(f"Failed to collect from {conf_config['name']}: {e}")

        self.log_result(len(leads))
        return leads

    def _collect_conference(self, conf_key: str, conf_config: Dict) -> List[RawLead]:
        """
        Collect from a specific conference.

        Note: This is a template implementation. Each conference has different
        HTML structure, so you'll need to customize the scraping logic.
        """
        leads = []

        try:
            # Attempt to scrape conference website
            response = requests.get(conf_config['url'], timeout=30)
            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch {conf_config['name']}: {response.status_code}")
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Example: Look for oral presentations
            # NOTE: This selector is a placeholder - actual selectors vary by conference
            oral_papers = soup.find_all('div', class_='oral-paper')

            for paper in oral_papers[:50]:  # Limit to top 50
                try:
                    # Extract author information
                    # NOTE: Customize these selectors for each conference
                    authors_elem = paper.find('div', class_='authors')
                    if not authors_elem:
                        continue

                    authors_text = authors_elem.get_text()
                    authors = [a.strip() for a in authors_text.split(',')]

                    # Extract title
                    title_elem = paper.find('h3', class_='title')
                    title = title_elem.get_text().strip() if title_elem else ''

                    # Extract affiliations (often in parentheses or separate div)
                    affiliation_elem = paper.find('div', class_='affiliation')
                    affiliation = affiliation_elem.get_text().strip() if affiliation_elem else ''

                    # Process each author
                    for idx, author_name in enumerate(authors):
                        # Filter for European affiliations
                        if affiliation:
                            if not self.is_european_affiliation(
                                affiliation,
                                settings.tier_1_universities,
                                settings.tier_2_universities
                            ):
                                continue

                        lead = RawLead(
                            name=author_name,
                            source='conference',
                            university_affiliation=affiliation,
                            source_url=conf_config['url'],
                            raw_data={
                                'conference_name': conf_config['name'],
                                'conference_prestige': conf_config['prestige'],
                                'type': 'oral',  # or extract from paper
                                'paper_title': title,
                                'is_first_author': (idx == 0),
                                'author_position': idx,
                                'months_old': 0,  # Conference is current year
                                'topic': title,
                            }
                        )

                        leads.append(lead)

                except Exception as e:
                    self.logger.warning(f"Failed to process paper: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scrape {conf_config['name']}: {e}")

        return leads

    def collect_from_openreview(self, conference: str, year: int) -> List[RawLead]:
        """
        Collect papers from OpenReview (used by NeurIPS, ICML, ICLR).

        OpenReview has an API that makes this more reliable than scraping.
        """
        leads = []

        try:
            # OpenReview API endpoint
            # Example for ICLR 2024: https://api.openreview.net/notes?invitation=ICLR.cc/2024/Conference/-/Blind_Submission
            api_url = f"https://api.openreview.net/notes"
            params = {
                'invitation': f'{conference}.cc/{year}/Conference/-/Blind_Submission',
                'details': 'replyCount,writable',
            }

            response = requests.get(api_url, params=params, timeout=30)
            if response.status_code != 200:
                return leads

            papers = response.json().get('notes', [])

            for paper in papers:
                # Filter for accepted papers (usually have specific tags)
                if 'accept' not in str(paper.get('content', {}).get('decision', '')).lower():
                    continue

                # Filter for oral presentations
                presentation_type = paper.get('content', {}).get('presentation_format', '')
                if 'oral' not in presentation_type.lower() and 'spotlight' not in presentation_type.lower():
                    continue

                # Extract authors
                authors = paper.get('content', {}).get('authors', [])
                title = paper.get('content', {}).get('title', '')

                for idx, author_name in enumerate(authors):
                    lead = RawLead(
                        name=author_name,
                        source='conference',
                        source_url=f"https://openreview.net/forum?id={paper.get('id')}",
                        raw_data={
                            'conference_name': conference,
                            'conference_prestige': 10,
                            'type': presentation_type,
                            'paper_title': title,
                            'is_first_author': (idx == 0),
                            'months_old': (datetime.now().year - year) * 12,
                            'topic': title,
                        }
                    )

                    leads.append(lead)

        except Exception as e:
            self.logger.error(f"Failed to collect from OpenReview: {e}")

        return leads
