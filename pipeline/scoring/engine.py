"""Enhanced scoring engine with momentum, negative signals, and readiness assessment."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from fuzzywuzzy import fuzz

from config.settings import settings
from pipeline.models import Lead, LeadSource
from pipeline.database import get_db


# Scoring weights by source
SCORING_WEIGHTS = {
    'arxiv': {
        'university_tier': 0.30,
        'first_author': 0.20,
        'recency': 0.15,
        'citations': 0.15,
        'topic_relevance': 0.20,
    },
    'github': {
        'european_location': 0.25,
        'followers': 0.20,
        'trending_owner': 0.20,
        'ai_topic': 0.20,
        'recent_activity': 0.15,
    },
    'spinoff': {
        'university_tier': 0.35,
        'recency': 0.25,
        'ai_relevance': 0.25,
        'team_size': 0.15,
    },
    'accelerator': {
        'accelerator_tier': 0.30,
        'cohort_recency': 0.25,
        'ai_relevance': 0.25,
        'funding_status': 0.20,
    },
    'hackathon': {
        'prize_tier': 0.30,
        'hackathon_prestige': 0.25,
        'project_ai_relevance': 0.25,
        'team_location': 0.20,
    },
    'eu_grant': {
        'grant_prestige': 0.35,
        'grant_amount': 0.25,
        'recency': 0.20,
        'ai_relevance': 0.20,
    },
    'conference': {
        'conference_prestige': 0.35,
        'presentation_type': 0.30,
        'recency': 0.20,
        'topic_relevance': 0.15,
    }
}

# Tier 1 accelerators
TIER_1_ACCELERATORS = [
    'Entrepreneurs First', 'Seedcamp', 'Techstars', 'Antler', 'Y Combinator'
]

# Hot AI topics (for keyword matching)
HOT_AI_TOPICS = [
    'llm', 'large language model', 'agent', 'robotics', 'foundation model',
    'diffusion', 'transformer', 'generative ai', 'rag', 'multimodal',
    'autonomous', 'reinforcement learning', 'computer vision', 'nlp',
    'drug discovery', 'protein folding', 'biotech ai'
]

# Negative signals
NEGATIVE_SIGNALS = {
    'already_funded': {
        'series_a_plus': -50,  # Remove from list
        'seed_round_6mo': -20,  # Likely already has investors
    },
    'geography': {
        'moved_to_us': -30,  # Less relevant for European fund
        'asia_based': -30,
    },
    'employment': {
        'big_tech_recent_join': -15,  # Just joined Google/Meta = not founding soon
        'tenured_professor': -10,  # Less likely to leave academia
    },
    'previous_founder': {
        'active_company': -25,  # Already running a company
        'recent_exit_24mo': +10,  # POSITIVE - serial founders are good targets
    }
}


class ScoringEngine:
    """Enhanced scoring engine with momentum and negative signals."""

    def __init__(self):
        self.settings = settings

    def calculate_score(self, lead: Lead, all_leads: Optional[List[Lead]] = None) -> float:
        """
        Calculate composite score for a lead.

        This includes:
        1. Base score from primary source
        2. Momentum bonus (multi-source)
        3. Network effects bonus
        4. Negative signal penalty
        """
        # 1. Calculate base score from primary source
        base_score = self._calculate_base_score(lead)

        # 2. Calculate momentum bonus (if we have all leads)
        momentum_bonus = 0.0
        if all_leads:
            momentum_bonus = self._calculate_momentum_bonus(lead, all_leads)

        # 3. Calculate network effects bonus
        network_bonus = self._calculate_network_score(lead)

        # 4. Calculate negative signal penalty
        negative_penalty = self._check_negative_signals(lead)

        # Total score
        total = base_score + momentum_bonus + network_bonus + negative_penalty

        # Update lead
        lead.preliminary_score = base_score
        lead.momentum_score = momentum_bonus
        lead.network_score = network_bonus
        lead.negative_signal_penalty = negative_penalty
        lead.total_score = max(0, total)  # Never go below 0

        return lead.total_score

    def _calculate_base_score(self, lead: Lead) -> float:
        """Calculate base score from primary source."""
        source = lead.primary_source
        if not source or source not in SCORING_WEIGHTS:
            return 0.0

        weights = SCORING_WEIGHTS[source]
        scores = {}

        # Get raw scores from lead's enrichment data
        raw_data = lead.enrichment_data or {}

        if source == 'arxiv':
            scores['university_tier'] = self._score_university(lead.university_affiliation)
            scores['first_author'] = 10 if raw_data.get('is_first_author') else 0
            scores['recency'] = self._score_recency_days(raw_data.get('days_old', 30))
            scores['citations'] = min(raw_data.get('citation_count', 0) * 2, 10)
            scores['topic_relevance'] = self._score_ai_topic(raw_data.get('topics', []))

        elif source == 'github':
            scores['european_location'] = 10 if raw_data.get('is_european') else 0
            scores['followers'] = min(raw_data.get('followers', 0) / 100, 10)
            scores['trending_owner'] = 10 if raw_data.get('trending_repo') else 0
            scores['ai_topic'] = self._score_ai_topic(raw_data.get('topics', []))
            scores['recent_activity'] = 10 if raw_data.get('recent_commits') else 5

        elif source == 'spinoff':
            scores['university_tier'] = self._score_university(lead.university_affiliation)
            scores['recency'] = self._score_recency_months(raw_data.get('months_old', 12))
            scores['ai_relevance'] = self._score_ai_topic([raw_data.get('sector', '')])
            scores['team_size'] = min(raw_data.get('team_size', 1) * 2, 10)

        elif source == 'accelerator':
            scores['accelerator_tier'] = self._score_accelerator(raw_data.get('accelerator'))
            scores['cohort_recency'] = self._score_recency_months(raw_data.get('months_since_demo', 12))
            scores['ai_relevance'] = self._score_ai_topic([raw_data.get('sector', '')])
            scores['funding_status'] = 5 if raw_data.get('unfunded') else 0

        elif source == 'hackathon':
            scores['prize_tier'] = 10 if 'first' in str(raw_data.get('prize', '')).lower() else 5
            scores['hackathon_prestige'] = self._score_hackathon(raw_data.get('hackathon_name'))
            scores['project_ai_relevance'] = self._score_ai_topic([raw_data.get('project_description', '')])
            scores['team_location'] = 10 if raw_data.get('is_european') else 0

        elif source == 'eu_grant':
            scores['grant_prestige'] = self._score_grant(raw_data.get('grant_type'))
            scores['grant_amount'] = min(raw_data.get('grant_amount', 0) / 100000, 10)  # €100k = 1 pt
            scores['recency'] = self._score_recency_months(raw_data.get('months_old', 12))
            scores['ai_relevance'] = self._score_ai_topic([raw_data.get('research_area', '')])

        elif source == 'conference':
            scores['conference_prestige'] = self._score_conference(raw_data.get('conference_name'))
            scores['presentation_type'] = self._score_presentation_type(raw_data.get('type'))
            scores['recency'] = self._score_recency_months(raw_data.get('months_old', 12))
            scores['topic_relevance'] = self._score_ai_topic([raw_data.get('topic', '')])

        # Calculate weighted total
        total = sum(
            scores.get(factor, 0) * weight
            for factor, weight in weights.items()
        )

        return round(total, 2)

    def _calculate_momentum_bonus(self, lead: Lead, all_leads: List[Lead]) -> float:
        """
        Calculate momentum bonus when same person appears in multiple sources.

        This is a VERY strong signal of building momentum toward founding.
        """
        # Find duplicates (same person from different sources)
        duplicates = self._find_duplicates(lead, all_leads)

        if len(duplicates) <= 1:
            return 0.0  # No duplicates

        # Count unique sources
        unique_sources = set()
        for dup_lead in duplicates:
            if hasattr(dup_lead, 'sources'):
                for source in dup_lead.sources:
                    unique_sources.add(source.source)
            elif dup_lead.primary_source:
                unique_sources.add(dup_lead.primary_source)

        source_count = len(unique_sources)

        # Momentum bonus based on source diversity
        momentum_bonus_map = {
            1: 0,    # Single source
            2: 10,   # Two sources - strong signal
            3: 20,   # Three sources - VERY strong signal
            4: 30,   # Four+ sources - extraordinary signal
        }

        bonus = momentum_bonus_map.get(source_count, 30)

        logger.debug(f"Lead '{lead.name}' found in {source_count} sources, momentum bonus: +{bonus}")

        return bonus

    def _find_duplicates(self, lead: Lead, all_leads: List[Lead]) -> List[Lead]:
        """Find potential duplicates using fuzzy name matching."""
        duplicates = [lead]

        for other_lead in all_leads:
            if other_lead.id == lead.id:
                continue

            # Fuzzy match names
            similarity = fuzz.ratio(
                lead.name.lower().strip(),
                other_lead.name.lower().strip()
            )

            if similarity >= 85:  # 85% similarity threshold
                duplicates.append(other_lead)

        return duplicates

    def _calculate_network_score(self, lead: Lead) -> float:
        """
        Calculate network effects score.

        Checks:
        - Same lab as successful spin-offs
        - Co-authors with prominent researchers
        """
        score = 0.0

        # Check if from a successful lab
        if lead.university_affiliation:
            affiliation_lower = lead.university_affiliation.lower()

            # ETH Zurich labs
            if 'eth' in affiliation_lower:
                if any(lab in affiliation_lower for lab in ['cvl', 'computer vision', 'asl', 'autonomous systems']):
                    score += 8

            # Oxford labs
            if 'oxford' in affiliation_lower:
                if any(lab in affiliation_lower for lab in ['robotics institute', 'deep medicine']):
                    score += 8

        # TODO: Check co-authors (requires maintaining a database of prominent researchers)

        return min(score, 15)  # Cap at 15 points

    def _check_negative_signals(self, lead: Lead) -> float:
        """
        Check for negative signals that reduce score.

        Returns negative penalty value.
        """
        penalty = 0.0
        raw_data = lead.enrichment_data or {}

        # Check funding status
        if raw_data.get('funding_stage') in ['Series A', 'Series B', 'Series C']:
            penalty -= 50  # Remove from list

        # Check geography (if moved to US)
        if lead.location and 'united states' in lead.location.lower():
            penalty -= 30

        # Check employment status
        current_company = raw_data.get('current_company', '').lower()
        big_tech = ['google', 'meta', 'amazon', 'microsoft', 'apple', 'facebook']

        if any(company in current_company for company in big_tech):
            # Check if recently joined
            if raw_data.get('employment_months', 999) < 12:
                penalty -= 15

        # Check if tenured professor
        if raw_data.get('is_tenured_professor'):
            penalty -= 10

        # Check if already running a company
        if raw_data.get('has_active_company'):
            penalty -= 25

        # POSITIVE: Recent exit (serial founder)
        if raw_data.get('recent_exit_months') and raw_data['recent_exit_months'] <= 24:
            penalty += 10  # Positive signal

        return penalty

    # Helper scoring functions

    def _score_university(self, affiliation: Optional[str]) -> float:
        """Score university affiliation."""
        if not affiliation:
            return 0.0

        affiliation_lower = affiliation.lower()

        for uni in settings.tier_1_universities:
            if uni.lower() in affiliation_lower:
                return 10.0

        for uni in settings.tier_2_universities:
            if uni.lower() in affiliation_lower:
                return 7.0

        return 3.0

    def _score_accelerator(self, accelerator: Optional[str]) -> float:
        """Score accelerator prestige."""
        if not accelerator:
            return 0.0

        for acc in TIER_1_ACCELERATORS:
            if acc.lower() in accelerator.lower():
                return 10.0

        return 5.0

    def _score_recency_days(self, days_old: int) -> float:
        """Score based on recency (days)."""
        if days_old <= 7:
            return 10.0
        elif days_old <= 30:
            return 7.0
        elif days_old <= 90:
            return 4.0
        return 1.0

    def _score_recency_months(self, months_old: int) -> float:
        """Score based on recency (months)."""
        if months_old <= 3:
            return 10.0
        elif months_old <= 6:
            return 7.0
        elif months_old <= 12:
            return 4.0
        return 1.0

    def _score_ai_topic(self, topics: List[str]) -> float:
        """Score AI topic relevance."""
        if not topics:
            return 0.0

        topic_text = ' '.join(str(t).lower() for t in topics)
        matches = sum(1 for topic in HOT_AI_TOPICS if topic in topic_text)

        return min(matches * 3, 10)

    def _score_hackathon(self, hackathon_name: Optional[str]) -> float:
        """Score hackathon prestige."""
        if not hackathon_name:
            return 5.0

        prestige_hackathons = ['superai', 'devpost google', 'microsoft ai', 'aws', 'openai']
        if any(h in hackathon_name.lower() for h in prestige_hackathons):
            return 10.0

        return 5.0

    def _score_grant(self, grant_type: Optional[str]) -> float:
        """Score grant prestige."""
        if not grant_type:
            return 5.0

        grant_type_lower = grant_type.lower()

        if 'erc' in grant_type_lower:
            if 'starting' in grant_type_lower:
                return 10.0  # ERC Starting Grant - best signal
            return 9.0

        if 'horizon' in grant_type_lower or 'h2020' in grant_type_lower:
            return 8.0

        return 5.0

    def _score_conference(self, conference_name: Optional[str]) -> float:
        """Score conference prestige."""
        if not conference_name:
            return 5.0

        conf_lower = conference_name.lower()

        top_tier = ['neurips', 'icml', 'iclr', 'cvpr', 'eccv', 'emnlp', 'acl']
        if any(conf in conf_lower for conf in top_tier):
            return 10.0

        second_tier = ['aaai', 'ijcai', 'iccv', 'naacl', 'coling']
        if any(conf in conf_lower for conf in second_tier):
            return 8.0

        return 5.0

    def _score_presentation_type(self, pres_type: Optional[str]) -> float:
        """Score presentation type (oral > poster)."""
        if not pres_type:
            return 5.0

        pres_lower = pres_type.lower()

        if 'oral' in pres_lower or 'spotlight' in pres_lower:
            return 10.0
        elif 'workshop organizer' in pres_lower:
            return 9.0
        elif 'tutorial' in pres_lower:
            return 8.0
        elif 'poster' in pres_lower:
            return 5.0

        return 5.0
