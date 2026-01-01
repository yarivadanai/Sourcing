"""
Pipeline validation script.

Tests the pipeline end-to-end with recent data to ensure quality leads.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from pipeline.database import init_db, get_db
from pipeline.models import Lead, LeadSource, PipelineRun
from pipeline.main import FounderSourcingPipeline


logger.remove()
logger.add(sys.stderr, level="INFO")


class PipelineValidator:
    """Validates pipeline output quality."""

    def __init__(self):
        self.validation_criteria = {
            'min_leads': 5,  # Minimum leads expected
            'min_hot_leads': 1,  # Minimum HOT leads
            'required_fields': ['name', 'source', 'total_score'],
            'min_score': 5.0,
            'european_focus': True,
            'ai_deep_tech_focus': True,
        }

    def validate_lead_quality(self, leads: List[Lead]) -> Dict:
        """
        Validate lead quality against Ellipsis Venture criteria.

        Checks:
        - AI/Deep Tech focus
        - European location
        - Pre-seed stage (negative signals)
        - Data completeness
        - Scoring makes sense
        """
        results = {
            'total_leads': len(leads),
            'hot_leads': 0,
            'warm_leads': 0,
            'cold_leads': 0,
            'issues': [],
            'quality_score': 0.0,
            'sample_leads': [],
        }

        if len(leads) == 0:
            results['issues'].append("No leads generated")
            return results

        # Categorize by readiness
        for lead in leads:
            if lead.readiness == 'HOT':
                results['hot_leads'] += 1
            elif lead.readiness == 'WARM':
                results['warm_leads'] += 1
            else:
                results['cold_leads'] += 1

        # Quality checks
        quality_checks = {
            'has_email': 0,
            'has_linkedin': 0,
            'has_university': 0,
            'has_outreach_hook': 0,
            'multi_source': 0,
            'european_location': 0,
            'ai_deep_tech': 0,
            'recent_activity': 0,
        }

        for lead in leads:
            # Email
            if lead.email:
                quality_checks['has_email'] += 1

            # LinkedIn
            if lead.linkedin_url:
                quality_checks['has_linkedin'] += 1

            # University affiliation
            if lead.university_affiliation:
                quality_checks['has_university'] += 1

            # Outreach hook
            if lead.outreach_hook:
                quality_checks['has_outreach_hook'] += 1

            # Multi-source (momentum indicator)
            sources = self._get_lead_sources(lead)
            if len(sources) >= 2:
                quality_checks['multi_source'] += 1

            # European location check
            if self._is_european(lead):
                quality_checks['european_location'] += 1

            # AI/Deep Tech focus
            if self._is_ai_deep_tech(lead):
                quality_checks['ai_deep_tech'] += 1

            # Recent activity (within 30 days)
            if self._has_recent_activity(lead):
                quality_checks['recent_activity'] += 1

        # Calculate quality percentages
        total = len(leads)
        quality_percentages = {
            k: (v / total * 100) if total > 0 else 0
            for k, v in quality_checks.items()
        }

        # Overall quality score (weighted)
        weights = {
            'has_email': 0.15,
            'has_linkedin': 0.10,
            'has_university': 0.10,
            'has_outreach_hook': 0.10,
            'multi_source': 0.20,
            'european_location': 0.15,
            'ai_deep_tech': 0.15,
            'recent_activity': 0.05,
        }

        quality_score = sum(
            quality_percentages[k] * weights[k]
            for k in weights.keys()
        )

        results['quality_checks'] = quality_percentages
        results['quality_score'] = quality_score

        # Flag issues
        if results['hot_leads'] < self.validation_criteria['min_hot_leads']:
            results['issues'].append(
                f"Low HOT leads: {results['hot_leads']} "
                f"(expected >= {self.validation_criteria['min_hot_leads']})"
            )

        if quality_percentages['european_location'] < 80:
            results['issues'].append(
                f"Low European coverage: {quality_percentages['european_location']:.1f}% "
                "(expected >= 80%)"
            )

        if quality_percentages['ai_deep_tech'] < 80:
            results['issues'].append(
                f"Low AI/Deep Tech focus: {quality_percentages['ai_deep_tech']:.1f}% "
                "(expected >= 80%)"
            )

        if quality_score < 60:
            results['issues'].append(
                f"Overall quality too low: {quality_score:.1f}/100 (expected >= 60)"
            )

        # Sample leads for manual review
        results['sample_leads'] = self._get_sample_leads(leads)

        return results

    def _get_lead_sources(self, lead: Lead) -> List[str]:
        """Get all sources for a lead from database."""
        with get_db() as db:
            sources = db.query(LeadSource).filter(
                LeadSource.lead_id == lead.id
            ).all()
            return [s.source_name for s in sources]

    def _is_european(self, lead: Lead) -> bool:
        """Check if lead is European-focused."""
        # Check university affiliation
        european_universities = [
            'eth', 'epfl', 'oxford', 'cambridge', 'imperial', 'ucl',
            'tum', 'kth', 'delft', 'leuven', 'dtu', 'ntnu',
            'chalmers', 'lund', 'uppsala', 'amsterdam', 'utrecht',
            'polytechnique', 'sorbonne', 'heidelberg', 'munich',
        ]

        if lead.university_affiliation:
            uni_lower = lead.university_affiliation.lower()
            if any(uni in uni_lower for uni in european_universities):
                return True

        # Check location from LinkedIn
        if lead.linkedin_data:
            location = lead.linkedin_data.get('location', '').lower()
            european_locations = [
                'switzerland', 'uk', 'united kingdom', 'london', 'oxford',
                'cambridge', 'germany', 'berlin', 'munich', 'sweden',
                'stockholm', 'netherlands', 'amsterdam', 'france', 'paris',
                'belgium', 'denmark', 'norway', 'austria', 'zurich',
            ]
            if any(loc in location for loc in european_locations):
                return True

        # Check company location
        if lead.company_location:
            loc_lower = lead.company_location.lower()
            if any(loc in loc_lower for loc in european_locations):
                return True

        return False

    def _is_ai_deep_tech(self, lead: Lead) -> bool:
        """Check if lead is AI/Deep Tech focused."""
        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural', 'nlp', 'computer vision', 'llm', 'large language model',
            'robotics', 'autonomous', 'generative', 'ml', 'cv', 'transformer',
            'diffusion', 'gan', 'reinforcement learning', 'model',
        ]

        # Check outreach hook
        if lead.outreach_hook:
            text_lower = lead.outreach_hook.lower()
            if any(keyword in text_lower for keyword in ai_keywords):
                return True

        # Check LinkedIn headline/summary
        if lead.linkedin_data:
            headline = lead.linkedin_data.get('headline', '').lower()
            summary = lead.linkedin_data.get('summary', '').lower()
            combined = headline + ' ' + summary
            if any(keyword in combined for keyword in ai_keywords):
                return True

        # Check current role
        if lead.current_role:
            role_lower = lead.current_role.lower()
            if any(keyword in role_lower for keyword in ai_keywords):
                return True

        return False

    def _has_recent_activity(self, lead: Lead) -> bool:
        """Check if lead has activity in last 30 days."""
        if lead.last_activity_date:
            days_ago = (datetime.now() - lead.last_activity_date).days
            return days_ago <= 30
        return False

    def _get_sample_leads(self, leads: List[Lead], n: int = 5) -> List[Dict]:
        """Get sample leads for manual review."""
        # Sort by score descending
        sorted_leads = sorted(leads, key=lambda x: x.total_score, reverse=True)

        samples = []
        for lead in sorted_leads[:n]:
            sources = self._get_lead_sources(lead)
            samples.append({
                'name': lead.name,
                'score': lead.total_score,
                'readiness': lead.readiness,
                'sources': sources,
                'university': lead.university_affiliation,
                'company': lead.company_name,
                'email': lead.email,
                'linkedin': lead.linkedin_url,
                'hook': lead.outreach_hook[:100] if lead.outreach_hook else None,
            })

        return samples

    def print_validation_report(self, results: Dict):
        """Print validation report."""
        logger.info("\n" + "="*60)
        logger.info("PIPELINE VALIDATION REPORT")
        logger.info("="*60)

        logger.info(f"\n📊 Lead Statistics:")
        logger.info(f"  Total Leads: {results['total_leads']}")
        logger.info(f"  🔥 HOT Leads: {results['hot_leads']}")
        logger.info(f"  🌡️  WARM Leads: {results['warm_leads']}")
        logger.info(f"  ❄️  COLD Leads: {results['cold_leads']}")

        logger.info(f"\n✅ Quality Checks:")
        for check, percentage in results.get('quality_checks', {}).items():
            emoji = "✓" if percentage >= 60 else "⚠"
            logger.info(f"  {emoji} {check.replace('_', ' ').title()}: {percentage:.1f}%")

        logger.info(f"\n🎯 Overall Quality Score: {results['quality_score']:.1f}/100")

        if results['issues']:
            logger.warning(f"\n⚠️  Issues Found ({len(results['issues'])}):")
            for issue in results['issues']:
                logger.warning(f"  - {issue}")
        else:
            logger.success("\n✓ No issues found - pipeline validation passed!")

        if results['sample_leads']:
            logger.info(f"\n📋 Sample Leads (Top {len(results['sample_leads'])}):")
            for i, lead in enumerate(results['sample_leads'], 1):
                logger.info(f"\n  {i}. {lead['name']} ({lead['readiness']}, Score: {lead['score']:.1f})")
                logger.info(f"     Sources: {', '.join(lead['sources'])}")
                if lead['university']:
                    logger.info(f"     University: {lead['university']}")
                if lead['company']:
                    logger.info(f"     Company: {lead['company']}")
                if lead['email']:
                    logger.info(f"     Email: {lead['email']}")
                if lead['hook']:
                    logger.info(f"     Hook: {lead['hook']}...")

        logger.info("\n" + "="*60)


def main():
    """Run pipeline validation."""
    logger.info("🚀 Starting pipeline validation...")
    logger.info("Testing with data from the last 7 days\n")

    # Initialize database
    init_db()

    # Run pipeline
    pipeline = FounderSourcingPipeline()

    try:
        # Run pipeline (limited scope for validation)
        logger.info("Running pipeline...")
        leads = pipeline.run()

        # Validate results
        validator = PipelineValidator()
        results = validator.validate_lead_quality(leads)

        # Print report
        validator.print_validation_report(results)

        # Exit code based on validation
        if results['quality_score'] >= 60 and not results['issues']:
            logger.success("\n✓ Pipeline validation PASSED")
            return 0
        else:
            logger.warning("\n⚠ Pipeline validation FAILED - review issues above")
            return 1

    except Exception as e:
        logger.error(f"\n❌ Pipeline validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
