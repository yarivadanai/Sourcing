"""Cost tracking system for API calls and services."""

from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from config.settings import settings
from pipeline.database import get_db
from pipeline.models import CostLog


# Operation cost mapping
OPERATION_COSTS = {
    'linkedin_basic': 0.01,  # Basic profile lookup
    'linkedin_full': 0.03,   # Full profile data
    'email_finding': 0.05,   # Hunter.io or Apollo
    'twitter_lookup': 0.0,   # Free tier
    'github_api': 0.0,       # Free
    'arxiv_api': 0.0,        # Free
    'crunchbase_lookup': 0.02,  # Per query
}


class CostTracker:
    """Track API costs to stay within budget."""

    def __init__(self, monthly_budget: Optional[float] = None):
        self.monthly_budget = monthly_budget or settings.monthly_budget
        self.current_month_spend = self._get_current_month_spend()
        logger.info(f"Cost tracker initialized: ${self.current_month_spend:.2f} spent this month")

    def _get_current_month_spend(self) -> float:
        """Get total spend for current month."""
        try:
            # Get first day of current month
            now = datetime.utcnow()
            first_day = datetime(now.year, now.month, 1)

            with get_db() as db:
                result = db.query(CostLog).filter(
                    CostLog.date >= first_day
                ).all()

                total = sum(log.cost for log in result)
                return total
        except Exception as e:
            logger.error(f"Failed to get current month spend: {e}")
            return 0.0

    def can_afford(self, operation: str, count: int = 1) -> bool:
        """
        Check if we can afford this operation.

        Args:
            operation: Operation name (e.g., 'linkedin_full')
            count: Number of operations to perform

        Returns:
            True if within budget, False otherwise
        """
        cost = OPERATION_COSTS.get(operation, 0) * count
        projected_total = self.current_month_spend + cost

        if projected_total > self.monthly_budget:
            logger.warning(
                f"Operation '{operation}' (${cost:.2f}) would exceed budget: "
                f"${projected_total:.2f} > ${self.monthly_budget:.2f}"
            )
            return False

        return True

    def log_cost(
        self,
        operation: str,
        cost: Optional[float] = None,
        service: Optional[str] = None,
        lead_id: Optional[int] = None,
        pipeline_run_id: Optional[int] = None,
        success: bool = True,
        notes: Optional[str] = None
    ) -> float:
        """
        Log API cost for tracking.

        Args:
            operation: Operation name
            cost: Actual cost (if None, uses OPERATION_COSTS)
            service: Service name (e.g., 'proxycurl')
            lead_id: Associated lead ID
            pipeline_run_id: Associated pipeline run ID
            success: Whether operation succeeded
            notes: Additional notes

        Returns:
            Cost logged
        """
        # Use default cost if not provided
        if cost is None:
            cost = OPERATION_COSTS.get(operation, 0.0)

        try:
            with get_db() as db:
                log = CostLog(
                    operation=operation,
                    service=service,
                    cost=cost,
                    lead_id=lead_id,
                    pipeline_run_id=pipeline_run_id,
                    success=success,
                    notes=notes
                )
                db.add(log)
                db.commit()

            self.current_month_spend += cost
            logger.debug(f"Logged cost: {operation} = ${cost:.4f}")

            return cost
        except Exception as e:
            logger.error(f"Failed to log cost: {e}")
            return 0.0

    def get_remaining_budget(self) -> float:
        """Get remaining budget for current month."""
        return max(0, self.monthly_budget - self.current_month_spend)

    def get_budget_status(self) -> dict:
        """Get detailed budget status."""
        remaining = self.get_remaining_budget()
        percentage_used = (self.current_month_spend / self.monthly_budget) * 100

        return {
            'monthly_budget': self.monthly_budget,
            'spent': self.current_month_spend,
            'remaining': remaining,
            'percentage_used': percentage_used,
            'status': 'OK' if percentage_used < 90 else 'WARNING' if percentage_used < 100 else 'EXCEEDED'
        }

    def get_cost_breakdown(self, days: int = 30) -> dict:
        """
        Get cost breakdown by operation for last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with cost breakdown
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            with get_db() as db:
                logs = db.query(CostLog).filter(
                    CostLog.date >= cutoff_date
                ).all()

                breakdown = {}
                for log in logs:
                    operation = log.operation
                    if operation not in breakdown:
                        breakdown[operation] = {
                            'count': 0,
                            'total_cost': 0.0,
                            'successful': 0,
                            'failed': 0
                        }

                    breakdown[operation]['count'] += 1
                    breakdown[operation]['total_cost'] += log.cost
                    if log.success:
                        breakdown[operation]['successful'] += 1
                    else:
                        breakdown[operation]['failed'] += 1

                return breakdown
        except Exception as e:
            logger.error(f"Failed to get cost breakdown: {e}")
            return {}

    def estimate_cost_for_leads(self, lead_count: int, with_enrichment: bool = True) -> dict:
        """
        Estimate cost for processing N leads.

        Args:
            lead_count: Number of leads
            with_enrichment: Whether to include enrichment costs

        Returns:
            Cost estimate breakdown
        """
        estimate = {
            'lead_count': lead_count,
            'operations': {},
            'total': 0.0
        }

        if with_enrichment:
            # Assume 80% get basic LinkedIn lookup
            linkedin_basic_count = int(lead_count * 0.8)
            linkedin_basic_cost = linkedin_basic_count * OPERATION_COSTS['linkedin_basic']
            estimate['operations']['linkedin_basic'] = {
                'count': linkedin_basic_count,
                'unit_cost': OPERATION_COSTS['linkedin_basic'],
                'total': linkedin_basic_cost
            }
            estimate['total'] += linkedin_basic_cost

            # Assume 30% get full profile
            linkedin_full_count = int(lead_count * 0.3)
            linkedin_full_cost = linkedin_full_count * OPERATION_COSTS['linkedin_full']
            estimate['operations']['linkedin_full'] = {
                'count': linkedin_full_count,
                'unit_cost': OPERATION_COSTS['linkedin_full'],
                'total': linkedin_full_cost
            }
            estimate['total'] += linkedin_full_cost

            # Assume 20% get email finding
            email_count = int(lead_count * 0.2)
            email_cost = email_count * OPERATION_COSTS['email_finding']
            estimate['operations']['email_finding'] = {
                'count': email_count,
                'unit_cost': OPERATION_COSTS['email_finding'],
                'total': email_cost
            }
            estimate['total'] += email_cost

        return estimate
