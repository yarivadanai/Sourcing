"""LinkedIn profile enrichment with smart strategy."""

import requests
from typing import Optional, Dict
from time import time
from loguru import logger

from config.settings import settings
from pipeline.cost_tracker import CostTracker
from pipeline.models import Lead


class LinkedInEnrichment:
    """
    LinkedIn profile enrichment using compliant third-party APIs.

    Uses Proxycurl API (recommended) or falls back to manual search.
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.api_key = settings.proxycurl_api_key
        self.cost_tracker = cost_tracker or CostTracker()
        self.base_url = "https://nubela.co/proxycurl/api"

    def enrich_lead(self, lead: Lead) -> Lead:
        """
        Enrich lead with LinkedIn profile using smart strategy.

        Strategy:
        - Score >= 7.5: Full profile enrichment
        - Score >= 5.0: Basic profile lookup
        - Score < 5.0: Skip enrichment (save cost)
        """
        # Check if already enriched
        if lead.linkedin_url:
            logger.debug(f"Lead '{lead.name}' already has LinkedIn URL")
            return lead

        # Smart enrichment based on score
        if lead.preliminary_score < 5.0:
            logger.debug(f"Skipping LinkedIn enrichment for '{lead.name}' (score {lead.preliminary_score:.1f} < 5.0)")
            return lead

        # Check budget
        operation = 'linkedin_full' if lead.preliminary_score >= 7.5 else 'linkedin_basic'
        if not self.cost_tracker.can_afford(operation):
            logger.warning(f"Cannot afford {operation} for '{lead.name}' - budget exceeded")
            return lead

        # Find LinkedIn profile
        start_time = time()
        linkedin_url = self._find_profile(lead.name, lead.company_name)
        enrichment_time = time() - start_time

        if not linkedin_url:
            logger.debug(f"LinkedIn profile not found for '{lead.name}'")
            return lead

        # Update lead
        lead.linkedin_url = linkedin_url

        # Log cost
        self.cost_tracker.log_cost(
            operation='linkedin_basic',
            service='proxycurl',
            lead_id=lead.id,
            success=True,
            notes=f"Found profile for {lead.name}"
        )

        # Get full profile if high score
        if lead.preliminary_score >= 7.5:
            profile_data = self._get_full_profile(linkedin_url)
            if profile_data:
                self._merge_profile_data(lead, profile_data)

                # Log additional cost
                self.cost_tracker.log_cost(
                    operation='linkedin_full',
                    service='proxycurl',
                    lead_id=lead.id,
                    success=True,
                    notes=f"Full profile for {lead.name}"
                )

        logger.info(f"Enriched '{lead.name}' with LinkedIn profile ({enrichment_time:.1f}s)")

        return lead

    def _find_profile(self, name: str, company: Optional[str] = None) -> Optional[str]:
        """
        Find LinkedIn profile URL by name and company.

        Uses Proxycurl Person Lookup Endpoint.
        """
        if not self.api_key:
            logger.warning("Proxycurl API key not configured")
            return None

        try:
            # Parse name
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            # Build API request
            url = f"{self.base_url}/linkedin/profile/resolve"
            params = {
                'first_name': first_name,
                'last_name': last_name,
            }

            if company:
                params['company_domain'] = self._extract_domain(company)

            headers = {'Authorization': f'Bearer {self.api_key}'}

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data.get('url')
            elif response.status_code == 404:
                logger.debug(f"Profile not found for {name}")
            else:
                logger.warning(f"Proxycurl API error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Failed to find LinkedIn profile for {name}: {e}")

        return None

    def _get_full_profile(self, linkedin_url: str) -> Optional[Dict]:
        """
        Get full profile data from LinkedIn URL.

        Uses Proxycurl Person Profile Endpoint.
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/v2/linkedin"
            params = {'url': linkedin_url}
            headers = {'Authorization': f'Bearer {self.api_key}'}

            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get profile data: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to get full profile: {e}")

        return None

    def _merge_profile_data(self, lead: Lead, profile_data: Dict):
        """Merge LinkedIn profile data into lead."""
        # Update basic fields
        if not lead.location and profile_data.get('city'):
            lead.location = profile_data['city']

        if not lead.country and profile_data.get('country'):
            lead.country = profile_data['country']

        # Store enrichment data
        if not lead.enrichment_data:
            lead.enrichment_data = {}

        # Add LinkedIn-specific data
        lead.enrichment_data['linkedin_headline'] = profile_data.get('headline')
        lead.enrichment_data['linkedin_summary'] = profile_data.get('summary', '')[:500]  # Truncate

        # Extract employment info
        experiences = profile_data.get('experiences', [])
        if experiences:
            current_exp = experiences[0]
            lead.enrichment_data['current_company'] = current_exp.get('company', {}).get('name')
            lead.enrichment_data['current_position'] = current_exp.get('title')
            lead.enrichment_data['currently_employed'] = current_exp.get('ends_at') is None

            # Check employment duration
            if current_exp.get('starts_at'):
                start_date = self._parse_date(current_exp['starts_at'])
                if start_date:
                    from datetime import datetime
                    months = (datetime.now() - start_date).days // 30
                    lead.enrichment_data['employment_months'] = months

            # Check if not currently employed (for readiness assessment)
            if current_exp.get('ends_at'):
                end_date = self._parse_date(current_exp['ends_at'])
                if end_date:
                    from datetime import datetime
                    days_since_left = (datetime.now() - end_date).days
                    lead.enrichment_data['days_since_left_job'] = days_since_left

        # Extract education
        education = profile_data.get('education', [])
        if education:
            # Check for PhD
            for edu in education:
                degree = edu.get('degree_name', '').lower()
                if 'phd' in degree or 'doctor' in degree:
                    lead.enrichment_data['has_phd'] = True

                    # Check PhD year
                    if edu.get('starts_at'):
                        start_date = self._parse_date(edu['starts_at'])
                        if start_date:
                            from datetime import datetime
                            years = (datetime.now() - start_date).days // 365
                            lead.enrichment_data['phd_year'] = years

        # Check for tenured professor
        if experiences and any('professor' in exp.get('title', '').lower() for exp in experiences):
            # Heuristic: if professor for > 5 years, likely tenured
            for exp in experiences:
                if 'professor' in exp.get('title', '').lower():
                    if exp.get('starts_at'):
                        start_date = self._parse_date(exp['starts_at'])
                        if start_date:
                            from datetime import datetime
                            years = (datetime.now() - start_date).days // 365
                            if years > 5:
                                lead.enrichment_data['is_tenured_professor'] = True

    def _extract_domain(self, company: str) -> str:
        """Extract domain from company name or URL."""
        if not company:
            return ''

        # If it's already a URL, extract domain
        if 'http' in company or '.' in company:
            from urllib.parse import urlparse
            try:
                domain = urlparse(company).netloc or company
                return domain.replace('www.', '')
            except Exception:
                pass

        # Convert company name to likely domain
        # This is a heuristic - may not always work
        domain = company.lower()
        domain = domain.replace(' ', '')
        domain = domain.replace('inc', '')
        domain = domain.replace('ltd', '')
        domain = domain.replace('.', '')

        return domain

    def _parse_date(self, date_dict: Dict) -> Optional['datetime']:
        """Parse Proxycurl date format."""
        try:
            from datetime import datetime
            year = date_dict.get('year')
            month = date_dict.get('month', 1)
            day = date_dict.get('day', 1)

            if year:
                return datetime(year, month, day)
        except Exception:
            pass

        return None

    def generate_search_url(self, name: str, company: Optional[str] = None) -> str:
        """
        Generate Google search URL for manual LinkedIn lookup.

        Useful for low-volume manual searches or as fallback.
        """
        query_parts = [f'site:linkedin.com/in/ "{name}"']

        if company:
            query_parts.append(f'"{company}"')

        query = ' '.join(query_parts)
        from urllib.parse import quote
        return f"https://www.google.com/search?q={quote(query)}"
