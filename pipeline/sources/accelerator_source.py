"""Accelerator portfolio companies data source."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class AcceleratorSource(BaseSource):
    """Collect leads from accelerator portfolio companies."""

    def __init__(self):
        super().__init__("accelerator")
        self.accelerators = self._get_accelerator_config()

    def _get_accelerator_config(self) -> Dict:
        """
        Configuration for all 22 target European accelerators.
        """
        return {
            'entrepreneurs_first': {
                'name': 'Entrepreneurs First',
                'portfolio_url': 'https://www.joinef.com/portfolio/',
                'tier': 1,
                'focus': ['deep-tech', 'ai', 'biotech'],
                'locations': ['london', 'paris', 'berlin'],
                'scoring_bonus': 10,
            },
            'techstars': {
                'name': 'Techstars',
                'portfolio_url': 'https://www.techstars.com/portfolio',
                'tier': 1,
                'focus': ['tech', 'ai'],
                'locations': ['london', 'berlin', 'paris', 'amsterdam'],
                'scoring_bonus': 9,
            },
            'antler': {
                'name': 'Antler',
                'portfolio_url': 'https://www.antler.co/portfolio',
                'tier': 1,
                'focus': ['tech', 'ai'],
                'locations': ['europe'],
                'scoring_bonus': 9,
            },
            'startup_wise_guys': {
                'name': 'Startup Wise Guys',
                'portfolio_url': 'https://startupwiseguys.com/portfolio/',
                'tier': 2,
                'focus': ['b2b-saas', 'fintech', 'cybersecurity'],
                'locations': ['tallinn', 'riga', 'vilnius'],
                'scoring_bonus': 7,
            },
            'seedcamp': {
                'name': 'Seedcamp',
                'portfolio_url': 'https://seedcamp.com/portfolio/',
                'tier': 1,
                'focus': ['tech', 'ai'],
                'locations': ['london'],
                'scoring_bonus': 10,
            },
            'heartfelt': {
                'name': 'HEARTFELT_',
                'portfolio_url': 'https://heartfelt.vc/portfolio',
                'tier': 2,
                'focus': ['deep-tech', 'ai', 'quantum'],
                'locations': ['switzerland'],
                'scoring_bonus': 8,
            },
            'rockstart': {
                'name': 'Rockstart',
                'portfolio_url': 'https://rockstart.com/portfolio/',
                'tier': 2,
                'focus': ['ai', 'energy', 'health'],
                'locations': ['amsterdam'],
                'scoring_bonus': 7,
            },
            'ndrc': {
                'name': 'NDRC',
                'portfolio_url': 'https://www.ndrc.ie/portfolio',
                'tier': 2,
                'focus': ['tech'],
                'locations': ['dublin', 'cork'],
                'scoring_bonus': 6,
            },
            'plug_and_play': {
                'name': 'Plug and Play Tech Center',
                'portfolio_url': 'https://www.plugandplaytechcenter.com/startups/',
                'tier': 1,
                'focus': ['tech', 'ai', 'mobility'],
                'locations': ['europe'],
                'scoring_bonus': 8,
            },
            'imec_istart': {
                'name': 'imec.istart',
                'portfolio_url': 'https://www.imec-int.com/en/istart',
                'tier': 2,
                'focus': ['deep-tech', 'chips', 'photonics'],
                'locations': ['leuven', 'belgium'],
                'scoring_bonus': 8,
            },
            'founders_factory': {
                'name': 'Founders Factory',
                'portfolio_url': 'https://foundersfactory.com/portfolio',
                'tier': 2,
                'focus': ['tech', 'ai'],
                'locations': ['london'],
                'scoring_bonus': 7,
            },
            'startupbootcamp': {
                'name': 'Startupbootcamp',
                'portfolio_url': 'https://www.startupbootcamp.org/alumni/',
                'tier': 2,
                'focus': ['tech'],
                'locations': ['europe'],
                'scoring_bonus': 6,
            },
            'bethnal_green': {
                'name': 'Bethnal Green Ventures',
                'portfolio_url': 'https://bethnalgreenventures.com/portfolio/',
                'tier': 2,
                'focus': ['tech-for-good', 'ai'],
                'locations': ['london'],
                'scoring_bonus': 6,
            },
            'wayra': {
                'name': 'Wayra',
                'portfolio_url': 'https://www.wayra.com/startups',
                'tier': 2,
                'focus': ['tech', 'ai'],
                'locations': ['london', 'munich', 'barcelona'],
                'scoring_bonus': 7,
            },
            'birdhouse': {
                'name': 'Birdhouse',
                'portfolio_url': 'https://birdhouse.fund/portfolio',
                'tier': 2,
                'focus': ['climate-tech', 'ai'],
                'locations': ['zurich'],
                'scoring_bonus': 7,
            },
            'accelerace': {
                'name': 'Accelerace',
                'portfolio_url': 'https://accelerace.io/portfolio/',
                'tier': 2,
                'focus': ['tech'],
                'locations': ['copenhagen'],
                'scoring_bonus': 6,
            },
            'sting': {
                'name': 'Sting',
                'portfolio_url': 'https://sting.co/startups/',
                'tier': 2,
                'focus': ['tech', 'ai'],
                'locations': ['stockholm'],
                'scoring_bonus': 7,
            },
            'tenity': {
                'name': 'Tenity',
                'portfolio_url': 'https://www.tenity.com/startups',
                'tier': 2,
                'focus': ['fintech', 'insurtech'],
                'locations': ['zurich', 'singapore'],
                'scoring_bonus': 6,
            },
            'demium': {
                'name': 'Demium',
                'portfolio_url': 'https://demium.com/portfolio/',
                'tier': 2,
                'focus': ['tech'],
                'locations': ['spain', 'portugal'],
                'scoring_bonus': 5,
            },
            'lventure_group': {
                'name': 'LVenture Group',
                'portfolio_url': 'https://lventuregroup.com/portfolio/',
                'tier': 2,
                'focus': ['digital', 'tech'],
                'locations': ['rome', 'milan'],
                'scoring_bonus': 5,
            },
            'hightechxl': {
                'name': 'HighTechXL',
                'portfolio_url': 'https://hightechxl.com/portfolio/',
                'tier': 2,
                'focus': ['deep-tech', 'hardware'],
                'locations': ['eindhoven'],
                'scoring_bonus': 8,
            },
            'norrsken_evolve': {
                'name': 'Norrsken Evolve',
                'portfolio_url': 'https://www.norrsken.org/evolve',
                'tier': 2,
                'focus': ['impact-tech', 'ai'],
                'locations': ['stockholm'],
                'scoring_bonus': 6,
            },
        }

    def collect(self) -> List[RawLead]:
        """Collect portfolio companies from all accelerators."""
        self.logger.info(f"Collecting from {len(self.accelerators)} accelerators")

        leads = []

        for accel_key, accel_config in self.accelerators.items():
            try:
                accel_leads = self._collect_accelerator(accel_key, accel_config)
                leads.extend(accel_leads)
                self.logger.info(f"{accel_config['name']}: {len(accel_leads)} companies")
            except Exception as e:
                self.logger.error(f"Failed to collect from {accel_config['name']}: {e}")

        self.log_result(len(leads))
        return leads

    def _collect_accelerator(self, accel_key: str, accel_config: Dict) -> List[RawLead]:
        """
        Collect portfolio companies from a specific accelerator.

        Note: Each accelerator has different website structure.
        For production, consider using Crunchbase/Tracxn API instead.
        """
        leads = []

        try:
            response = requests.get(accel_config['portfolio_url'], timeout=30)
            if response.status_code != 200:
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for portfolio companies
            # NOTE: Selectors vary by accelerator - this is a template
            company_items = soup.find_all('div', class_='portfolio-company')  # Placeholder

            for item in company_items:
                try:
                    # Extract company name
                    name_elem = item.find('h3') or item.find('h2')
                    if not name_elem:
                        continue
                    company_name = name_elem.get_text().strip()

                    # Extract description
                    desc_elem = item.find('p', class_='description')
                    description = desc_elem.get_text().strip() if desc_elem else ''

                    # Filter for AI/Deep Tech
                    if not self._is_ai_related(description):
                        continue

                    # Extract founder names (if available)
                    founders_elem = item.find('div', class_='founders')
                    founders = []
                    if founders_elem:
                        founders_text = founders_elem.get_text()
                        founders = [f.strip() for f in founders_text.split(',')]

                    # Extract website
                    website_elem = item.find('a', class_='website')
                    website = website_elem['href'] if website_elem else None

                    # Extract cohort/batch info
                    cohort_elem = item.find('span', class_='cohort')
                    cohort = cohort_elem.get_text().strip() if cohort_elem else None
                    months_since_demo = self._calculate_months_since_cohort(cohort)

                    # Filter for recent cohorts (last 2 years)
                    if months_since_demo > 24:
                        continue

                    # Check funding status (prefer unfunded)
                    funding_elem = item.find('span', class_='funding')
                    unfunded = not funding_elem or 'pre-seed' in funding_elem.get_text().lower()

                    # Create leads for each founder
                    if not founders:
                        founders = [f"Founder of {company_name}"]

                    for founder_name in founders:
                        lead = RawLead(
                            name=founder_name,
                            source='accelerator',
                            company_name=company_name,
                            company_website=website,
                            source_url=accel_config['portfolio_url'],
                            raw_data={
                                'accelerator': accel_config['name'],
                                'accelerator_tier': accel_config['tier'],
                                'cohort': cohort,
                                'months_since_demo': months_since_demo,
                                'sector': description,
                                'unfunded': unfunded,
                                'focus_areas': accel_config['focus'],
                            }
                        )

                        leads.append(lead)

                except Exception as e:
                    self.logger.warning(f"Failed to process company: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scrape {accel_config['name']}: {e}")

        return leads

    def _is_ai_related(self, text: str) -> bool:
        """Check if description is AI/Deep Tech related."""
        if not text:
            return False

        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural', 'nlp', 'computer vision', 'robotics', 'autonomous',
            'llm', 'large language', 'generative', 'foundation model',
            'biotech', 'drug discovery', 'quantum', 'deep tech',
            'semiconductor', 'photonics', 'hardware ai'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ai_keywords)

    def _calculate_months_since_cohort(self, cohort: Optional[str]) -> int:
        """Calculate months since cohort/demo day."""
        if not cohort:
            return 0  # Unknown - treat as recent

        try:
            # Try to extract year from cohort name (e.g., "Batch 2024", "W24", "Spring 2024")
            import re

            # Look for 4-digit year
            year_match = re.search(r'20\d{2}', cohort)
            if year_match:
                year = int(year_match.group())
                current_year = datetime.now().year
                return (current_year - year) * 12

            # Look for YC-style batch codes (W24, S24, etc.)
            batch_match = re.search(r'([WS])(\d{2})', cohort)
            if batch_match:
                season = batch_match.group(1)
                year_suffix = int(batch_match.group(2))
                year = 2000 + year_suffix

                # W = Winter (Jan), S = Summer (June)
                month_offset = 0 if season == 'W' else 6

                current_date = datetime.now()
                cohort_date = datetime(year, 1 + month_offset, 1)
                delta = current_date - cohort_date
                return int(delta.days / 30)

        except Exception:
            pass

        return 0  # Unknown - treat as recent

    def collect_from_crunchbase(self, accelerator_name: str) -> List[RawLead]:
        """
        Collect portfolio from Crunchbase API (if API key available).

        This is more reliable than web scraping but requires paid subscription.
        """
        leads = []

        if not settings.crunchbase_api_key:
            self.logger.warning("Crunchbase API key not configured")
            return leads

        try:
            api_url = "https://api.crunchbase.com/api/v4/searches/organizations"

            payload = {
                "field_ids": ["identifier", "short_description", "founded_on", "website_url", "rank_org"],
                "query": [
                    {
                        "type": "predicate",
                        "field_id": "investor_identifiers",
                        "operator_id": "includes",
                        "values": [accelerator_name]
                    },
                    {
                        "type": "predicate",
                        "field_id": "funding_stage",
                        "operator_id": "includes",
                        "values": ["seed", "pre_seed"]
                    },
                    {
                        "type": "predicate",
                        "field_id": "location_identifiers",
                        "operator_id": "includes",
                        "values": ["europe"]
                    }
                ],
                "limit": 100
            }

            headers = {
                "X-cb-user-key": settings.crunchbase_api_key,
                "Content-Type": "application/json"
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                companies = data.get('entities', [])

                for company in companies:
                    # Extract company details
                    properties = company.get('properties', {})

                    # Filter for AI companies
                    description = properties.get('short_description', '')
                    if not self._is_ai_related(description):
                        continue

                    # Create lead (will need to look up founders separately)
                    lead = RawLead(
                        name=f"Founder of {properties.get('identifier', {}).get('value')}",
                        source='accelerator',
                        company_name=properties.get('identifier', {}).get('value'),
                        company_website=properties.get('website_url'),
                        source_url=f"https://www.crunchbase.com/organization/{properties.get('identifier', {}).get('permalink')}",
                        raw_data={
                            'accelerator': accelerator_name,
                            'sector': description,
                            'founded_on': properties.get('founded_on'),
                            'unfunded': True,  # Filtered for seed/pre-seed
                        }
                    )

                    leads.append(lead)

        except Exception as e:
            self.logger.error(f"Failed to collect from Crunchbase for {accelerator_name}: {e}")

        return leads
