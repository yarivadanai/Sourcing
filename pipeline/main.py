"""Main pipeline orchestrator for the sourcing engine."""

import sys
from datetime import datetime
from typing import List
from loguru import logger
from fuzzywuzzy import fuzz

from config.settings import settings
from pipeline.database import init_db, get_db
from pipeline.models import Lead, LeadSource
from pipeline.monitoring import PipelineMonitor
from pipeline.cost_tracker import CostTracker
from pipeline.scoring.engine import ScoringEngine
from pipeline.scoring.readiness import ReadinessAssessment
from pipeline.sources.base import RawLead
from pipeline.sources.arxiv_source import ArxivSource
from pipeline.sources.eu_grants_source import EUGrantsSource

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/pipeline_{time}.log", rotation="1 week", retention="1 month", level="DEBUG")


class FounderSourcingPipeline:
    """Main pipeline for sourcing founders."""

    def __init__(self):
        self.monitor = PipelineMonitor()
        self.cost_tracker = CostTracker()
        self.scoring_engine = ScoringEngine()
        self.readiness_assessment = ReadinessAssessment()

    def run(self):
        """Execute the full weekly sourcing pipeline."""
        logger.info("=" * 70)
        logger.info("Starting Founder Sourcing Pipeline")
        logger.info(f"Run ID: {self.monitor.metrics.run_id}")
        logger.info("=" * 70)

        try:
            # Step 1: Collect from all sources
            logger.info("\n📊 STEP 1: Collecting from data sources...")
            raw_leads = self._collect_from_all_sources()
            logger.info(f"Collected {len(raw_leads)} raw leads from all sources")

            # Step 2: Deduplicate and save to database
            logger.info("\n🔍 STEP 2: Deduplicating and saving leads...")
            leads = self._deduplicate_and_save(raw_leads)
            logger.info(f"After deduplication: {len(leads)} unique leads")

            # Step 3: Score all leads
            logger.info("\n⭐ STEP 3: Scoring leads...")
            self._score_leads(leads)

            # Step 4: Assess readiness
            logger.info("\n🎯 STEP 4: Assessing readiness...")
            self._assess_readiness(leads)

            # Step 5: Update metrics
            self._update_metrics(leads)

            # Step 6: Generate output
            logger.info("\n📤 STEP 5: Generating output...")
            self._generate_output(leads)

            # Complete monitoring
            self.monitor.complete('completed')

            logger.info("\n✅ Pipeline completed successfully!")

        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
            self.monitor.log_error(str(e))
            self.monitor.complete('failed')
            raise

    def _collect_from_all_sources(self) -> List[RawLead]:
        """Collect leads from all configured data sources."""
        all_leads = []

        # Source 1: ArXiv
        try:
            arxiv_source = ArxivSource()
            arxiv_leads = arxiv_source.collect()
            all_leads.extend(arxiv_leads)
            self.monitor.log_source_result('arxiv', len(arxiv_leads), True)
        except Exception as e:
            logger.error(f"ArXiv source failed: {e}")
            self.monitor.log_source_result('arxiv', 0, False)
            self.monitor.log_error(str(e), 'arxiv')

        # Source 2: EU Grants
        try:
            grants_source = EUGrantsSource()
            grants_leads = grants_source.collect()
            all_leads.extend(grants_leads)
            self.monitor.log_source_result('eu_grant', len(grants_leads), True)
        except Exception as e:
            logger.error(f"EU Grants source failed: {e}")
            self.monitor.log_source_result('eu_grant', 0, False)
            self.monitor.log_error(str(e), 'eu_grant')

        # TODO: Add more sources:
        # - Conference speakers
        # - GitHub trending
        # - University spin-offs
        # - Accelerators
        # - Hackathons

        return all_leads

    def _deduplicate_and_save(self, raw_leads: List[RawLead]) -> List[Lead]:
        """Deduplicate leads and save to database."""
        leads = []
        duplicates_count = 0

        with get_db() as db:
            for raw_lead in raw_leads:
                # Normalize name for matching
                normalized_name = self._normalize_name(raw_lead.name)

                # Check if lead already exists
                existing_lead = db.query(Lead).filter(
                    Lead.normalized_name == normalized_name
                ).first()

                if existing_lead:
                    # Update existing lead
                    duplicates_count += 1
                    existing_lead.source_count += 1
                    existing_lead.last_updated = datetime.utcnow()

                    # Add new source reference
                    lead_source = LeadSource(
                        lead_id=existing_lead.id,
                        source=raw_lead.source,
                        source_url=raw_lead.source_url,
                        raw_data=raw_lead.raw_data
                    )
                    db.add(lead_source)

                    leads.append(existing_lead)

                else:
                    # Create new lead
                    new_lead = Lead(
                        name=raw_lead.name,
                        normalized_name=normalized_name,
                        email=raw_lead.email,
                        linkedin_url=raw_lead.linkedin_url,
                        github_profile=raw_lead.github_profile,
                        twitter_handle=raw_lead.twitter_handle,
                        university_affiliation=raw_lead.university_affiliation,
                        company_name=raw_lead.company_name,
                        company_website=raw_lead.company_website,
                        location=raw_lead.location,
                        primary_source=raw_lead.source,
                        enrichment_data=raw_lead.raw_data,
                        status='new'
                    )
                    db.add(new_lead)
                    db.flush()  # Get ID

                    # Add source reference
                    lead_source = LeadSource(
                        lead_id=new_lead.id,
                        source=raw_lead.source,
                        source_url=raw_lead.source_url,
                        raw_data=raw_lead.raw_data
                    )
                    db.add(lead_source)

                    leads.append(new_lead)

            db.commit()

        self.monitor.metrics.duplicates_found = duplicates_count
        return leads

    def _normalize_name(self, name: str) -> str:
        """Normalize name for deduplication."""
        # Remove extra spaces, convert to lowercase
        normalized = ' '.join(name.lower().strip().split())
        return normalized

    def _score_leads(self, leads: List[Lead]):
        """Score all leads."""
        with get_db() as db:
            for lead in leads:
                score = self.scoring_engine.calculate_score(lead, leads)
                logger.debug(f"Scored '{lead.name}': {score:.2f}")

            db.commit()

    def _assess_readiness(self, leads: List[Lead]):
        """Assess readiness for all leads."""
        with get_db() as db:
            for lead in leads:
                readiness = self.readiness_assessment.assess(lead)
                lead.readiness = readiness
                logger.debug(f"Readiness for '{lead.name}': {readiness}")

            db.commit()

    def _update_metrics(self, leads: List[Lead]):
        """Update monitoring metrics."""
        # Count new vs updated leads
        new_leads = sum(1 for l in leads if l.source_count == 1)
        updated_leads = sum(1 for l in leads if l.source_count > 1)

        # Count qualified leads
        qualified_leads = [l for l in leads if l.total_score >= settings.min_score_threshold]
        hot_leads = [l for l in qualified_leads if l.readiness == 'hot']
        warm_leads = [l for l in qualified_leads if l.readiness == 'warm']
        cold_leads = [l for l in qualified_leads if l.readiness == 'cold']

        # Calculate average score
        avg_score = sum(l.total_score for l in leads) / len(leads) if leads else 0

        self.monitor.update_lead_counts(
            new=new_leads,
            updated=updated_leads,
            qualified=len(qualified_leads),
            hot=len(hot_leads),
            warm=len(warm_leads),
            cold=len(cold_leads)
        )
        self.monitor.metrics.avg_score = avg_score

    def _generate_output(self, leads: List[Lead]):
        """Generate segmented output files."""
        # Filter qualified leads
        qualified_leads = [l for l in leads if l.total_score >= settings.min_score_threshold]

        # Segment by readiness
        hot_leads = [l for l in qualified_leads if l.readiness == 'hot']
        warm_leads = [l for l in qualified_leads if l.readiness == 'warm']
        cold_leads = [l for l in qualified_leads if l.readiness == 'cold']

        # Generate CSV files
        timestamp = datetime.now().strftime('%Y%m%d')

        if hot_leads:
            self._export_csv(hot_leads, f"output/hot_leads_{timestamp}.csv")
            logger.info(f"📄 Exported {len(hot_leads)} HOT leads")

        if warm_leads:
            self._export_csv(warm_leads, f"output/warm_leads_{timestamp}.csv")
            logger.info(f"📄 Exported {len(warm_leads)} WARM leads")

        if cold_leads:
            self._export_csv(cold_leads, f"output/cold_leads_{timestamp}.csv")
            logger.info(f"📄 Exported {len(cold_leads)} COLD leads")

    def _export_csv(self, leads: List[Lead], filename: str):
        """Export leads to CSV."""
        import csv

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'rank', 'name', 'score', 'readiness', 'source', 'sources_count',
                'company', 'linkedin', 'email', 'location', 'university',
                'background', 'primary_source', 'date_added'
            ])
            writer.writeheader()

            for rank, lead in enumerate(sorted(leads, key=lambda x: x.total_score, reverse=True), 1):
                writer.writerow({
                    'rank': rank,
                    'name': lead.name,
                    'score': f"{lead.total_score:.2f}",
                    'readiness': lead.readiness,
                    'source': lead.primary_source,
                    'sources_count': lead.source_count,
                    'company': lead.company_name or '',
                    'linkedin': lead.linkedin_url or '',
                    'email': lead.email or '',
                    'location': lead.location or '',
                    'university': lead.university_affiliation or '',
                    'background': self._generate_background(lead),
                    'primary_source': lead.primary_source,
                    'date_added': lead.first_seen_date.strftime('%Y-%m-%d')
                })

    def _generate_background(self, lead: Lead) -> str:
        """Generate background summary for lead."""
        parts = []

        if lead.university_affiliation:
            parts.append(f"Researcher at {lead.university_affiliation}")

        if lead.primary_source == 'arxiv':
            raw_data = lead.enrichment_data or {}
            if raw_data.get('is_first_author'):
                parts.append(f"First author on: {raw_data.get('paper_title', '')[:50]}...")

        if lead.company_name:
            parts.append(f"Company: {lead.company_name}")

        if lead.source_count > 1:
            parts.append(f"Found in {lead.source_count} sources")

        return " | ".join(parts)


def main():
    """Main entry point."""
    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Run pipeline
    pipeline = FounderSourcingPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
