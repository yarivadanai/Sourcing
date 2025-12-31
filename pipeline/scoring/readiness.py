"""Readiness assessment to determine how close someone is to founding."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from pipeline.models import Lead


class ReadinessAssessment:
    """Assess how ready a lead is to found a company."""

    READINESS_SIGNALS = {
        'hot': [
            'recently_left_position',
            'multiple_recent_projects',
            'building_in_public',
            'launched_mvp',
            'applied_to_accelerators',
            'active_github_last_30d',
            'recent_paper_and_repo',
            'seeking_cofounders',
        ],
        'warm': [
            'active_github_last_90d',
            'recent_conference_talk',
            'multiple_data_sources',
            'grant_recipient',
            'hackathon_winner',
            'university_spinoff_in_progress',
        ],
        'cold': [
            'tenured_professor',
            'phd_student_early',
            'big_tech_recent_join',
            'no_recent_activity',
        ]
    }

    def assess(self, lead: Lead) -> str:
        """
        Assess readiness of a lead.

        Returns:
            'hot', 'warm', or 'cold'
        """
        signals = self._detect_signals(lead)

        # Count signals
        hot_signals = sum(1 for s in signals if s in self.READINESS_SIGNALS['hot'])
        cold_signals = sum(1 for s in signals if s in self.READINESS_SIGNALS['cold'])
        warm_signals = sum(1 for s in signals if s in self.READINESS_SIGNALS['warm'])

        # Store signals in lead
        lead.readiness_signals = signals

        # Decision logic
        if cold_signals >= 2:
            return 'cold'

        if hot_signals >= 2:
            return 'hot'

        if hot_signals >= 1 or warm_signals >= 2:
            return 'warm'

        return 'warm'  # Default to warm

    def _detect_signals(self, lead: Lead) -> List[str]:
        """Detect readiness signals from lead data."""
        signals = []
        raw_data = lead.enrichment_data or {}

        # Check employment status
        if not raw_data.get('currently_employed'):
            # Recently left position
            if raw_data.get('days_since_left_job', 999) < 90:
                signals.append('recently_left_position')

        # Check GitHub activity
        if lead.github_profile:
            recent_commits = raw_data.get('github_commits_last_30d', 0)
            if recent_commits > 50:
                signals.append('active_github_last_30d')
            elif recent_commits > 10:
                signals.append('active_github_last_90d')

        # Check for multiple recent projects
        if raw_data.get('recent_project_count', 0) >= 3:
            signals.append('multiple_recent_projects')

        # Check for MVP/demo
        if raw_data.get('has_demo') or raw_data.get('has_mvp'):
            signals.append('launched_mvp')

        # Check Twitter for "building in public"
        if raw_data.get('building_in_public_tweets'):
            signals.append('building_in_public')

        # Check if applied to accelerators
        if raw_data.get('applied_to_accelerators'):
            signals.append('applied_to_accelerators')

        # Check for seeking cofounders
        if raw_data.get('seeking_cofounders'):
            signals.append('seeking_cofounders')

        # Check if recent paper + GitHub repo
        has_recent_paper = lead.primary_source == 'arxiv' and raw_data.get('days_old', 999) < 30
        has_active_repo = lead.github_profile and raw_data.get('github_commits_last_30d', 0) > 10
        if has_recent_paper and has_active_repo:
            signals.append('recent_paper_and_repo')

        # Check for multiple data sources (indicates momentum)
        if lead.source_count >= 3:
            signals.append('multiple_data_sources')

        # Check if recent grant recipient
        if lead.primary_source == 'eu_grant' and raw_data.get('months_old', 999) < 6:
            signals.append('grant_recipient')

        # Check if hackathon winner
        if lead.primary_source == 'hackathon' and raw_data.get('months_old', 999) < 6:
            signals.append('hackathon_winner')

        # Check if conference speaker
        if lead.primary_source == 'conference' and raw_data.get('months_old', 999) < 6:
            signals.append('recent_conference_talk')

        # Check if university spinoff
        if lead.primary_source == 'spinoff' and raw_data.get('months_old', 999) < 12:
            signals.append('university_spinoff_in_progress')

        # COLD signals

        # Check if tenured professor
        if raw_data.get('is_tenured_professor'):
            signals.append('tenured_professor')

        # Check if early PhD student
        if raw_data.get('phd_year') and raw_data['phd_year'] <= 1:
            signals.append('phd_student_early')

        # Check if recently joined big tech
        current_company = raw_data.get('current_company', '').lower()
        big_tech = ['google', 'meta', 'amazon', 'microsoft', 'apple', 'facebook']
        if any(company in current_company for company in big_tech):
            if raw_data.get('employment_months', 999) < 12:
                signals.append('big_tech_recent_join')

        # Check for no recent activity
        has_activity = (
            raw_data.get('github_commits_last_90d', 0) > 0 or
            raw_data.get('days_old', 999) < 90 or
            raw_data.get('twitter_posts_last_30d', 0) > 5
        )
        if not has_activity:
            signals.append('no_recent_activity')

        logger.debug(f"Readiness signals for '{lead.name}': {signals}")

        return signals

    def generate_readiness_explanation(self, lead: Lead) -> str:
        """Generate human-readable explanation of readiness assessment."""
        if not lead.readiness:
            return "Readiness not assessed"

        signals = lead.readiness_signals or []

        if lead.readiness == 'hot':
            return f"HOT lead: {', '.join(signals[:3])}"
        elif lead.readiness == 'warm':
            return f"WARM lead: {', '.join(signals[:2])}"
        else:
            return f"COLD lead: {', '.join(signals[:2])}"
