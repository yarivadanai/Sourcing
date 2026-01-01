"""Patent database source (European Patent Office)."""

import requests
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class PatentSource(BaseSource):
    """Collect leads from patent filings (EPO - European Patent Office)."""

    def __init__(self):
        super().__init__("patent")
        self.epo_api_base = "https://ops.epo.org/3.2/rest-services"

    def collect(self) -> List[RawLead]:
        """
        Collect recent patent filings from EPO.

        Note: EPO OPS API requires registration and API key.
        This is a template implementation.
        """
        self.logger.info("Collecting patent filings from EPO")

        leads = []

        # Search for AI/ML patents from target universities
        for university in settings.tier_1_universities + settings.tier_2_universities:
            try:
                uni_leads = self._search_patents_by_assignee(university)
                leads.extend(uni_leads)
            except Exception as e:
                self.logger.error(f"Failed to search patents for {university}: {e}")

        self.log_result(len(leads))
        return leads

    def _search_patents_by_assignee(self, assignee: str) -> List[RawLead]:
        """
        Search patents by assignee (university).

        EPO OPS API requires authentication.
        For production, you'd need to:
        1. Register at https://developers.epo.org/
        2. Get API credentials
        3. Implement OAuth authentication
        """
        leads = []

        # This is a placeholder - actual implementation requires EPO API credentials
        # Example query structure:
        # https://ops.epo.org/3.2/rest-services/published-data/search
        # ?q=pa=(ETH Zurich) AND IPC=(G06N)

        try:
            # AI/ML related IPC (International Patent Classification) codes
            ai_ipc_codes = [
                'G06N',  # Computer systems based on specific computational models
                'G06K9',  # Methods or arrangements for reading or recognizing printed/written characters or for recognizing patterns
                'G06F15',  # Digital computers in general
            ]

            # Search query (simplified example)
            query = f'pa="{assignee}" AND (IPC=G06N OR IPC=G06K9)'

            # Note: Actual EPO API requires authentication token
            # This is just showing the structure

            self.logger.debug(f"Would search EPO for: {query}")

            # Placeholder return
            # In production, parse EPO XML/JSON response

        except Exception as e:
            self.logger.error(f"Failed to search patents: {e}")

        return leads

    def _search_google_patents(self, assignee: str) -> List[RawLead]:
        """
        Alternative: Search Google Patents (no API key required).

        Google Patents provides a searchable interface.
        """
        leads = []

        try:
            # Google Patents search URL
            # Example: https://patents.google.com/?assignee=ETH+Zurich&q=artificial+intelligence

            # AI keywords
            ai_keywords = ['artificial intelligence', 'machine learning', 'neural network']

            for keyword in ai_keywords:
                search_url = f"https://patents.google.com/?assignee={assignee}&q={keyword.replace(' ', '+')}"

                response = requests.get(search_url, timeout=30)

                if response.status_code == 200:
                    # Parse HTML to extract patent information
                    # This would require BeautifulSoup parsing of Google Patents results
                    self.logger.debug(f"Fetched Google Patents for {assignee} - {keyword}")

                    # Extract inventor names from patents
                    # Create leads

        except Exception as e:
            self.logger.error(f"Failed to search Google Patents: {e}")

        return leads

    def _create_lead_from_patent(self, patent_data: Dict) -> Optional[RawLead]:
        """Create lead from patent data."""
        try:
            # Extract inventor names
            inventors = patent_data.get('inventors', [])
            if not inventors:
                return None

            # Use first inventor (typically lead researcher)
            inventor_name = inventors[0].get('name')
            if not inventor_name:
                return None

            # Extract patent details
            title = patent_data.get('title')
            abstract = patent_data.get('abstract', '')
            filing_date_str = patent_data.get('filing_date')
            assignee = patent_data.get('assignee')

            # Calculate months since filing
            months_old = 0
            if filing_date_str:
                try:
                    filing_date = datetime.fromisoformat(filing_date_str)
                    months_old = (datetime.now() - filing_date).days // 30
                except Exception:
                    pass

            lead = RawLead(
                name=inventor_name,
                source='patent',
                university_affiliation=assignee,
                source_url=patent_data.get('url'),
                raw_data={
                    'patent_title': title,
                    'abstract': abstract[:500],  # Truncate
                    'filing_date': filing_date_str,
                    'months_old': months_old,
                    'assignee': assignee,
                    'inventors': [inv.get('name') for inv in inventors],
                    'ipc_codes': patent_data.get('ipc_codes', []),
                }
            )

            return lead

        except Exception as e:
            self.logger.warning(f"Failed to create lead from patent: {e}")
            return None
