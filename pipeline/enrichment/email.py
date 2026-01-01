"""Email finding integration using Hunter.io or Apollo.io."""

import requests
from typing import Optional
from loguru import logger

from config.settings import settings
from pipeline.cost_tracker import CostTracker
from pipeline.models import Lead


class EmailFinder:
    """
    Find email addresses using Hunter.io or Apollo.io.

    Uses smart strategy to minimize costs.
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.hunter_api_key = settings.hunter_io_api_key
        self.cost_tracker = cost_tracker or CostTracker()

    def find_email(self, lead: Lead) -> Lead:
        """
        Find email for lead using smart strategy.

        Strategy:
        - Score >= 7.5: Use paid email finding service
        - Score < 7.5: Skip email finding (save cost)
        - Already has email: Skip
        """
        # Check if already has email
        if lead.email:
            logger.debug(f"Lead '{lead.name}' already has email")
            return lead

        # Only find email for high-scoring leads
        if lead.preliminary_score < 7.5:
            logger.debug(f"Skipping email finding for '{lead.name}' (score {lead.preliminary_score:.1f} < 7.5)")
            return lead

        # Check budget
        if not self.cost_tracker.can_afford('email_finding'):
            logger.warning(f"Cannot afford email finding for '{lead.name}' - budget exceeded")
            return lead

        # Try to find email
        email = None

        # Method 1: Use domain if company website is known
        if lead.company_website:
            email = self._find_email_by_domain(lead.name, lead.company_website)

        # Method 2: Try university email if affiliation is known
        if not email and lead.university_affiliation:
            email = self._guess_university_email(lead.name, lead.university_affiliation)

        if email:
            lead.email = email
            logger.info(f"Found email for '{lead.name}': {email}")

            # Log cost
            self.cost_tracker.log_cost(
                operation='email_finding',
                service='hunter.io',
                lead_id=lead.id,
                success=True,
                notes=f"Found email for {lead.name}"
            )
        else:
            logger.debug(f"Email not found for '{lead.name}'")

        return lead

    def _find_email_by_domain(self, name: str, domain: str) -> Optional[str]:
        """
        Find email using Hunter.io Email Finder API.

        https://hunter.io/api-documentation/v2#email-finder
        """
        if not self.hunter_api_key:
            logger.warning("Hunter.io API key not configured")
            return None

        try:
            # Clean domain
            domain = self._extract_domain(domain)

            # Parse name
            name_parts = name.split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            # Hunter.io Email Finder endpoint
            url = "https://api.hunter.io/v2/email-finder"
            params = {
                'domain': domain,
                'first_name': first_name,
                'last_name': last_name,
                'api_key': self.hunter_api_key
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                email_data = data.get('data', {})

                # Check confidence score
                confidence = email_data.get('score', 0)
                if confidence >= 50:  # At least 50% confidence
                    return email_data.get('email')
                else:
                    logger.debug(f"Low confidence email for {name}: {confidence}%")
            elif response.status_code == 401:
                logger.error("Hunter.io API authentication failed")
            else:
                logger.warning(f"Hunter.io API error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Failed to find email via Hunter.io: {e}")

        return None

    def _guess_university_email(self, name: str, university: str) -> Optional[str]:
        """
        Guess university email based on common patterns.

        This is a heuristic and may not always be correct.
        Consider verifying with email verification API.
        """
        # University domain mapping
        university_domains = {
            'ETH Zurich': 'ethz.ch',
            'EPFL': 'epfl.ch',
            'University of Oxford': 'ox.ac.uk',
            'University of Cambridge': 'cam.ac.uk',
            'Imperial College': 'imperial.ac.uk',
            'UCL': 'ucl.ac.uk',
            'TUM': 'tum.de',
            'KTH': 'kth.se',
            'TU Delft': 'tudelft.nl',
            'University of Amsterdam': 'uva.nl',
        }

        # Find matching university
        domain = None
        for uni_name, uni_domain in university_domains.items():
            if uni_name.lower() in university.lower():
                domain = uni_domain
                break

        if not domain:
            return None

        # Parse name
        name_parts = name.split()
        if len(name_parts) < 2:
            return None

        first_name = name_parts[0].lower()
        last_name = name_parts[-1].lower()

        # Common patterns
        patterns = [
            f"{first_name}.{last_name}@{domain}",
            f"{first_name[0]}{last_name}@{domain}",
            f"{first_name}_{last_name}@{domain}",
            f"{last_name}@{domain}",
        ]

        # Return first pattern (would need verification in production)
        # For production, use an email verification API to check which pattern is valid
        return patterns[0]

    def verify_email(self, email: str) -> bool:
        """
        Verify email address using Hunter.io Email Verifier.

        Returns True if email is valid and deliverable.
        """
        if not self.hunter_api_key:
            return False

        try:
            url = "https://api.hunter.io/v2/email-verifier"
            params = {
                'email': email,
                'api_key': self.hunter_api_key
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                result = data.get('data', {}).get('result', '')

                return result == 'deliverable'

        except Exception as e:
            logger.error(f"Failed to verify email: {e}")

        return False

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL or company website."""
        from urllib.parse import urlparse

        try:
            if not url.startswith('http'):
                url = f"https://{url}"

            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except Exception:
            return url
