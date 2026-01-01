"""Analytics and feedback loop for continuous improvement."""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func
from loguru import logger

from pipeline.database import get_db
from pipeline.models import Lead, LeadSource, OutreachHistory, PipelineRun


class Analytics:
    """Analytics engine for pipeline performance and lead quality."""

    def __init__(self):
        pass

    def generate_pipeline_report(self, days: int = 30) -> Dict:
        """
        Generate comprehensive pipeline performance report.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with pipeline metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with get_db() as db:
            # Pipeline runs in period
            runs = db.query(PipelineRun).filter(
                PipelineRun.start_time >= cutoff_date
            ).all()

            # Lead metrics
            total_leads = db.query(Lead).filter(
                Lead.first_seen_date >= cutoff_date
            ).count()

            qualified_leads = db.query(Lead).filter(
                Lead.first_seen_date >= cutoff_date,
                Lead.total_score >= 6.0
            ).count()

            # Source breakdown
            source_breakdown = self._get_source_breakdown(db, cutoff_date)

            # Score distribution
            score_distribution = self._get_score_distribution(db, cutoff_date)

            # Readiness breakdown
            readiness_breakdown = self._get_readiness_breakdown(db, cutoff_date)

            # Multi-source momentum
            momentum_analysis = self._analyze_momentum(db, cutoff_date)

            report = {
                'period_days': days,
                'pipeline_runs': len(runs),
                'total_leads': total_leads,
                'qualified_leads': qualified_leads,
                'qualification_rate': (qualified_leads / total_leads * 100) if total_leads > 0 else 0,
                'source_breakdown': source_breakdown,
                'score_distribution': score_distribution,
                'readiness_breakdown': readiness_breakdown,
                'momentum_analysis': momentum_analysis,
            }

            return report

    def analyze_source_performance(self) -> Dict[str, Dict]:
        """
        Analyze performance of each data source.

        Metrics:
        - Total leads from source
        - Average score
        - Qualification rate
        - Response rate (if outreach data available)
        """
        with get_db() as db:
            sources = ['arxiv', 'eu_grant', 'conference', 'github', 'spinoff', 'accelerator',
                      'hackathon', 'patent', 'twitter', 'blog']

            source_performance = {}

            for source in sources:
                # Get leads from this primary source
                leads = db.query(Lead).filter(Lead.primary_source == source).all()

                if not leads:
                    continue

                # Calculate metrics
                total_count = len(leads)
                avg_score = sum(l.total_score for l in leads) / total_count
                qualified_count = sum(1 for l in leads if l.total_score >= 6.0)
                qualification_rate = (qualified_count / total_count * 100) if total_count > 0 else 0

                # Outreach metrics (if available)
                contacted_count = sum(1 for l in leads if l.contacted_count > 0)
                responded_count = sum(1 for l in leads if l.responded)

                response_rate = (responded_count / contacted_count * 100) if contacted_count > 0 else 0

                source_performance[source] = {
                    'total_leads': total_count,
                    'avg_score': round(avg_score, 2),
                    'qualified_count': qualified_count,
                    'qualification_rate': round(qualification_rate, 1),
                    'contacted_count': contacted_count,
                    'responded_count': responded_count,
                    'response_rate': round(response_rate, 1),
                }

            return source_performance

    def analyze_scoring_effectiveness(self) -> Dict:
        """
        Analyze scoring system effectiveness.

        Check if high scores correlate with successful outcomes.
        """
        with get_db() as db:
            # Get leads with outreach history
            leads_with_outreach = db.query(Lead).filter(
                Lead.contacted_count > 0
            ).all()

            if not leads_with_outreach:
                return {
                    'message': 'No outreach data yet',
                    'recommendation': 'Start outreach to collect data for analysis'
                }

            # Group by score ranges
            score_ranges = {
                'excellent (8-10)': [],
                'good (6-8)': [],
                'fair (4-6)': [],
                'poor (0-4)': [],
            }

            for lead in leads_with_outreach:
                score = lead.total_score
                if score >= 8:
                    range_key = 'excellent (8-10)'
                elif score >= 6:
                    range_key = 'good (6-8)'
                elif score >= 4:
                    range_key = 'fair (4-6)'
                else:
                    range_key = 'poor (0-4)'

                score_ranges[range_key].append(lead)

            # Calculate response rates by score range
            analysis = {}
            for range_key, leads in score_ranges.items():
                if not leads:
                    continue

                responded = sum(1 for l in leads if l.responded)
                response_rate = (responded / len(leads) * 100) if leads else 0

                analysis[range_key] = {
                    'count': len(leads),
                    'responded': responded,
                    'response_rate': round(response_rate, 1)
                }

            return analysis

    def recommend_scoring_adjustments(self) -> List[str]:
        """
        Recommend adjustments to scoring weights based on data.

        Returns:
            List of recommendations
        """
        recommendations = []

        # Analyze source performance
        source_perf = self.analyze_source_performance()

        # Find best and worst performing sources
        sources_with_data = {k: v for k, v in source_perf.items() if v['contacted_count'] > 10}

        if not sources_with_data:
            return ["Not enough outreach data yet for recommendations"]

        # Sort by response rate
        sorted_sources = sorted(sources_with_data.items(), key=lambda x: x[1]['response_rate'], reverse=True)

        if len(sorted_sources) >= 2:
            best_source = sorted_sources[0]
            worst_source = sorted_sources[-1]

            if best_source[1]['response_rate'] > worst_source[1]['response_rate'] * 1.5:
                recommendations.append(
                    f"✅ Source '{best_source[0]}' has {best_source[1]['response_rate']:.1f}% response rate. "
                    f"Consider increasing its scoring weight."
                )
                recommendations.append(
                    f"⚠️ Source '{worst_source[0]}' has only {worst_source[1]['response_rate']:.1f}% response rate. "
                    f"Consider decreasing its scoring weight or improving filtering."
                )

        # Analyze multi-source momentum
        with get_db() as db:
            multi_source_leads = db.query(Lead).filter(Lead.source_count >= 2).all()

            if multi_source_leads:
                multi_response_rate = sum(1 for l in multi_source_leads if l.responded) / len(multi_source_leads) * 100
                single_source_leads = db.query(Lead).filter(Lead.source_count == 1, Lead.contacted_count > 0).all()

                if single_source_leads:
                    single_response_rate = sum(1 for l in single_source_leads if l.responded) / len(single_source_leads) * 100

                    if multi_response_rate > single_response_rate * 1.3:
                        recommendations.append(
                            f"🔥 Multi-source leads ({multi_response_rate:.1f}% response) outperform "
                            f"single-source ({single_response_rate:.1f}%). Momentum scoring is working well!"
                        )

        return recommendations

    def _get_source_breakdown(self, db, cutoff_date) -> Dict[str, int]:
        """Get lead count by source."""
        results = db.query(
            Lead.primary_source,
            func.count(Lead.id)
        ).filter(
            Lead.first_seen_date >= cutoff_date
        ).group_by(Lead.primary_source).all()

        return {source: count for source, count in results}

    def _get_score_distribution(self, db, cutoff_date) -> Dict[str, int]:
        """Get distribution of scores."""
        leads = db.query(Lead.total_score).filter(
            Lead.first_seen_date >= cutoff_date
        ).all()

        distribution = {
            '8-10 (excellent)': 0,
            '6-8 (good)': 0,
            '4-6 (fair)': 0,
            '0-4 (poor)': 0,
        }

        for (score,) in leads:
            if score >= 8:
                distribution['8-10 (excellent)'] += 1
            elif score >= 6:
                distribution['6-8 (good)'] += 1
            elif score >= 4:
                distribution['4-6 (fair)'] += 1
            else:
                distribution['0-4 (poor)'] += 1

        return distribution

    def _get_readiness_breakdown(self, db, cutoff_date) -> Dict[str, int]:
        """Get distribution of readiness levels."""
        results = db.query(
            Lead.readiness,
            func.count(Lead.id)
        ).filter(
            Lead.first_seen_date >= cutoff_date,
            Lead.readiness.isnot(None)
        ).group_by(Lead.readiness).all()

        return {readiness or 'unknown': count for readiness, count in results}

    def _analyze_momentum(self, db, cutoff_date) -> Dict:
        """Analyze multi-source momentum effectiveness."""
        # Count leads by source count
        results = db.query(
            Lead.source_count,
            func.count(Lead.id),
            func.avg(Lead.total_score)
        ).filter(
            Lead.first_seen_date >= cutoff_date
        ).group_by(Lead.source_count).all()

        momentum_data = {}
        for source_count, lead_count, avg_score in results:
            momentum_data[f'{source_count}_sources'] = {
                'count': lead_count,
                'avg_score': round(avg_score, 2) if avg_score else 0
            }

        return momentum_data


class FeedbackLoop:
    """Feedback loop for learning from outreach outcomes."""

    def __init__(self):
        self.analytics = Analytics()

    def record_outreach(
        self,
        lead_id: int,
        method: str,
        message: str
    ):
        """Record an outreach attempt."""
        from pipeline.database import get_db
        from pipeline.models import OutreachHistory

        with get_db() as db:
            outreach = OutreachHistory(
                lead_id=lead_id,
                contacted_date=datetime.utcnow(),
                method=method,
                message_content=message,
            )
            db.add(outreach)

            # Update lead
            lead = db.query(Lead).get(lead_id)
            if lead:
                lead.status = 'contacted'
                lead.contacted_count += 1
                lead.last_contacted = datetime.utcnow()

            db.commit()

        logger.info(f"Recorded outreach for lead {lead_id} via {method}")

    def record_response(
        self,
        lead_id: int,
        responded: bool,
        meeting_scheduled: bool = False,
        notes: Optional[str] = None
    ):
        """Record outcome of outreach."""
        from pipeline.database import get_db
        from pipeline.models import OutreachHistory

        with get_db() as db:
            # Update most recent outreach
            outreach = db.query(OutreachHistory).filter(
                OutreachHistory.lead_id == lead_id
            ).order_by(OutreachHistory.contacted_date.desc()).first()

            if outreach:
                outreach.responded = responded
                outreach.response_date = datetime.utcnow()
                outreach.notes = notes

                if meeting_scheduled:
                    outreach.outcome = 'qualified'
                    outreach.meeting_scheduled = True

            # Update lead
            lead = db.query(Lead).get(lead_id)
            if lead:
                lead.responded = responded

                if meeting_scheduled:
                    lead.status = 'qualified'
                    lead.meeting_scheduled = True
                elif responded:
                    lead.status = 'responded'

            db.commit()

        logger.info(f"Recorded response for lead {lead_id}: responded={responded}, meeting={meeting_scheduled}")

    def generate_insights(self) -> Dict:
        """Generate insights from feedback data."""
        source_perf = self.analytics.analyze_source_performance()
        scoring_effectiveness = self.analytics.analyze_scoring_effectiveness()
        recommendations = self.analytics.recommend_scoring_adjustments()

        return {
            'source_performance': source_perf,
            'scoring_effectiveness': scoring_effectiveness,
            'recommendations': recommendations,
        }
