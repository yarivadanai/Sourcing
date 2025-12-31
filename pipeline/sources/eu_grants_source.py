"""EU Research Grants data source (ERC, Horizon Europe)."""

import requests
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class EUGrantsSource(BaseSource):
    """Collect leads from EU research grant databases."""

    def __init__(self):
        super().__init__("eu_grant")
        self.cordis_api_base = "https://cordis.europa.eu/api/v1"

    def collect(self) -> List[RawLead]:
        """Collect grant recipients from EU databases."""
        self.logger.info("Collecting EU grant recipients")

        leads = []

        # Collect from ERC grants
        erc_leads = self._collect_erc_grants()
        leads.extend(erc_leads)

        # Collect from Horizon Europe
        horizon_leads = self._collect_horizon_europe()
        leads.extend(horizon_leads)

        self.log_result(len(leads))
        return leads

    def _collect_erc_grants(self, years_back: int = 2) -> List[RawLead]:
        """
        Collect ERC grant recipients.

        Focus on ERC Starting Grants (early career = more likely to found).
        """
        self.logger.info("Collecting ERC grants")
        leads = []

        # AI/ML related topics
        ai_topics = [
            "Artificial Intelligence",
            "Machine Learning",
            "Computer Vision",
            "Natural Language Processing",
            "Robotics",
            "Deep Learning"
        ]

        try:
            # CORDIS API for ERC grants
            # Note: This is a simplified example - actual API may require different parameters
            for topic in ai_topics:
                params = {
                    'programme': 'ERC',
                    'keywords': topic,
                    'contentType': 'project',
                    'pageSize': 50,
                }

                response = requests.get(
                    f"{self.cordis_api_base}/projects",
                    params=params,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    projects = data.get('projects', [])

                    for project in projects:
                        lead = self._process_grant(project, 'ERC')
                        if lead:
                            leads.append(lead)

        except Exception as e:
            self.logger.error(f"Failed to collect ERC grants: {e}")

        return leads

    def _collect_horizon_europe(self) -> List[RawLead]:
        """Collect Horizon Europe grant recipients in AI categories."""
        self.logger.info("Collecting Horizon Europe grants")
        leads = []

        # This is a placeholder - actual implementation would query Horizon Europe database
        # Similar to ERC grants above

        return leads

    def _process_grant(self, project: Dict, grant_program: str) -> Optional[RawLead]:
        """Process a grant project and extract lead."""
        try:
            # Extract Principal Investigator (PI)
            pi_name = project.get('coordinator', {}).get('name')
            if not pi_name:
                return None

            # Extract institution
            institution = project.get('coordinator', {}).get('organizationName')

            # Check if European institution
            if not institution or not self.is_european_affiliation(
                institution,
                settings.tier_1_universities,
                settings.tier_2_universities
            ):
                return None

            # Extract grant details
            grant_amount = project.get('totalCost', 0)
            start_date_str = project.get('startDate')
            start_date = datetime.fromisoformat(start_date_str) if start_date_str else datetime.now()
            months_old = (datetime.now() - start_date).days // 30

            # Determine grant type
            grant_type = project.get('title', '')
            if 'Starting Grant' in grant_type:
                grant_type = 'ERC Starting Grant'
            elif 'ERC' in grant_program:
                grant_type = 'ERC Grant'
            else:
                grant_type = f'{grant_program} Grant'

            lead = RawLead(
                name=pi_name,
                source='eu_grant',
                university_affiliation=institution,
                source_url=project.get('url'),
                raw_data={
                    'grant_type': grant_type,
                    'grant_amount': grant_amount,
                    'grant_program': grant_program,
                    'project_title': project.get('title'),
                    'research_area': project.get('topics', ['AI'])[0] if project.get('topics') else 'AI',
                    'start_date': start_date.isoformat(),
                    'months_old': months_old,
                    'project_id': project.get('id'),
                }
            )

            return lead

        except Exception as e:
            self.logger.warning(f"Failed to process grant: {e}")
            return None
