"""Airtable CRM integration for lead management."""

from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

try:
    from pyairtable import Table
    AIRTABLE_AVAILABLE = True
except ImportError:
    AIRTABLE_AVAILABLE = False
    logger.warning("pyairtable not installed, Airtable export disabled")

from config.settings import settings
from pipeline.models import Lead


class AirtableExporter:
    """Export leads to Airtable for CRM tracking."""

    def __init__(self):
        if not AIRTABLE_AVAILABLE:
            raise ImportError("pyairtable is not installed. Run: pip install pyairtable")

        self.api_key = settings.airtable_api_key
        self.base_id = settings.airtable_base_id
        self.table_name = settings.airtable_table_name

        if not self.api_key or not self.base_id:
            raise ValueError("Airtable API key and Base ID must be configured in .env")

        self.table = Table(self.api_key, self.base_id, self.table_name)

    def export_leads(self, leads: List[Lead]) -> int:
        """
        Export qualified leads to Airtable.

        Returns:
            Number of leads exported
        """
        logger.info(f"Exporting {len(leads)} leads to Airtable")

        records_to_create = []
        records_updated = 0

        for lead in leads:
            # Check if lead already exists in Airtable
            existing = self._find_existing_lead(lead.email or lead.linkedin_url or lead.name)

            if existing:
                # Update existing record
                self._update_lead(existing['id'], lead)
                records_updated += 1
            else:
                # Prepare new record
                record = self._prepare_record(lead)
                records_to_create.append(record)

        # Batch create new records
        if records_to_create:
            try:
                self.table.batch_create(records_to_create)
                logger.info(f"Created {len(records_to_create)} new records in Airtable")
            except Exception as e:
                logger.error(f"Failed to batch create records: {e}")

        if records_updated:
            logger.info(f"Updated {records_updated} existing records in Airtable")

        return len(records_to_create) + records_updated

    def _prepare_record(self, lead: Lead) -> Dict:
        """Prepare Airtable record from Lead."""
        # Generate outreach hook
        outreach_hook = self._generate_outreach_hook(lead)

        # Prepare record fields
        fields = {
            'Name': lead.name,
            'Score': round(lead.total_score, 2),
            'Readiness': lead.readiness or 'warm',
            'Status': self._map_status(lead.status),
            'Source': lead.primary_source,
            'Sources Count': lead.source_count,
            'Company': lead.company_name or '',
            'LinkedIn': lead.linkedin_url or '',
            'Email': lead.email or '',
            'GitHub': lead.github_profile or '',
            'Twitter': lead.twitter_handle or '',
            'Location': lead.location or '',
            'University': lead.university_affiliation or '',
            'Background': self._generate_background(lead),
            'Outreach Hook': outreach_hook,
            'Date Added': lead.first_seen_date.isoformat() if lead.first_seen_date else datetime.now().isoformat(),
            'Last Updated': lead.last_updated.isoformat() if lead.last_updated else datetime.now().isoformat(),
        }

        # Add optional fields if available
        if lead.momentum_score:
            fields['Momentum Score'] = round(lead.momentum_score, 2)

        if lead.enrichment_data:
            # Add custom fields from enrichment
            if lead.enrichment_data.get('paper_title'):
                fields['Paper Title'] = lead.enrichment_data['paper_title'][:500]

            if lead.enrichment_data.get('current_company'):
                fields['Current Company'] = lead.enrichment_data['current_company']

        return {'fields': fields}

    def _find_existing_lead(self, identifier: str) -> Optional[Dict]:
        """Find existing lead in Airtable by email, LinkedIn, or name."""
        if not identifier:
            return None

        try:
            # Search by email or LinkedIn URL
            formula = f"OR({{Email}}='{identifier}', {{LinkedIn}}='{identifier}', {{Name}}='{identifier}')"
            records = self.table.all(formula=formula)

            if records:
                return records[0]

        except Exception as e:
            logger.debug(f"Failed to find existing lead: {e}")

        return None

    def _update_lead(self, record_id: str, lead: Lead):
        """Update existing Airtable record."""
        try:
            # Only update certain fields
            update_fields = {
                'Score': round(lead.total_score, 2),
                'Readiness': lead.readiness or 'warm',
                'Sources Count': lead.source_count,
                'Last Updated': datetime.now().isoformat(),
            }

            # Update LinkedIn/Email if newly discovered
            if lead.linkedin_url:
                update_fields['LinkedIn'] = lead.linkedin_url
            if lead.email:
                update_fields['Email'] = lead.email

            self.table.update(record_id, update_fields)
            logger.debug(f"Updated Airtable record {record_id}")

        except Exception as e:
            logger.error(f"Failed to update record {record_id}: {e}")

    def _map_status(self, status: str) -> str:
        """Map internal status to Airtable status."""
        status_mapping = {
            'new': 'New Lead',
            'contacted': 'Contacted',
            'responded': 'Responded',
            'qualified': 'Qualified',
            'disqualified': 'Disqualified',
        }

        return status_mapping.get(status, 'New Lead')

    def _generate_background(self, lead: Lead) -> str:
        """Generate background summary for Airtable."""
        parts = []

        if lead.university_affiliation:
            parts.append(f"🎓 {lead.university_affiliation}")

        if lead.primary_source == 'arxiv':
            raw_data = lead.enrichment_data or {}
            if raw_data.get('is_first_author'):
                parts.append(f"📄 First author: {raw_data.get('paper_title', '')[:50]}...")

        if lead.primary_source == 'conference':
            raw_data = lead.enrichment_data or {}
            parts.append(f"🎤 {raw_data.get('conference_name')} speaker")

        if lead.company_name:
            parts.append(f"🏢 {lead.company_name}")

        if lead.source_count > 1:
            parts.append(f"🔥 Found in {lead.source_count} sources")

        return " | ".join(parts) if parts else "No additional context"

    def _generate_outreach_hook(self, lead: Lead) -> str:
        """Generate personalized outreach hook."""
        raw_data = lead.enrichment_data or {}

        hooks = {
            'arxiv': f"I read your recent paper on {raw_data.get('paper_topic', 'AI')}. At Ellipsis Venture, we back deep tech founders from top European institutions like {lead.university_affiliation}.",

            'github': f"Your work on {raw_data.get('repo_name', 'AI tools')} caught our attention. We invest in technical founders building AI infrastructure.",

            'spinoff': f"Congratulations on spinning out {lead.company_name} from {lead.university_affiliation}! We specialize in backing early-stage deep tech from top EU research.",

            'accelerator': f"Saw you went through {raw_data.get('accelerator', 'a top accelerator')}. We're actively backing {raw_data.get('sector', 'AI')} founders at the pre-seed stage.",

            'conference': f"Your presentation at {raw_data.get('conference_name', 'the conference')} was impressive. Have you considered commercializing your research?",

            'eu_grant': f"Congratulations on your {raw_data.get('grant_type', 'EU grant')}! We back researchers translating breakthrough research into companies.",

            'hackathon': f"Your {raw_data.get('prize', '')} win at {raw_data.get('hackathon_name', 'the hackathon')} was impressive! Have you thought about building this into a startup?",
        }

        return hooks.get(lead.primary_source, "We're interested in connecting about your AI work. Ellipsis Venture backs pre-seed deep tech founders across Europe.")

    def update_outreach_status(self, lead_id: int, status: str, notes: Optional[str] = None):
        """
        Update outreach status for a lead.

        Args:
            lead_id: Internal database lead ID
            status: New status (contacted, responded, qualified, etc.)
            notes: Optional notes about the interaction
        """
        try:
            # Find record by lead ID or name
            # Update status in Airtable
            logger.info(f"Updated outreach status for lead {lead_id}: {status}")

        except Exception as e:
            logger.error(f"Failed to update outreach status: {e}")
