"""Monitoring and alerting framework for the sourcing engine."""

import uuid
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import requests
from loguru import logger

from config.settings import settings
from pipeline.database import get_db
from pipeline.models import PipelineRun


@dataclass
class PipelineMetrics:
    """Track pipeline performance metrics."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_date: datetime = field(default_factory=datetime.utcnow)

    # Collection metrics
    sources_attempted: int = 0
    sources_successful: int = 0
    total_raw_leads: int = 0
    leads_by_source: Dict[str, int] = field(default_factory=dict)

    # Processing metrics
    duplicates_found: int = 0
    enrichment_attempts: int = 0
    enrichment_successful: int = 0
    avg_enrichment_time: float = 0.0

    # Scoring metrics
    avg_score: float = 0.0
    qualified_leads: int = 0  # Score >= threshold
    hot_leads: int = 0
    warm_leads: int = 0
    cold_leads: int = 0

    # Output metrics
    new_leads: int = 0  # Not in database before
    updated_leads: int = 0  # Existing leads with new sources

    # Errors
    errors: List[str] = field(default_factory=list)
    api_rate_limits_hit: List[str] = field(default_factory=list)

    # Cost tracking
    total_cost: float = 0.0
    cost_by_operation: Dict[str, float] = field(default_factory=dict)

    @property
    def enrichment_success_rate(self) -> float:
        """Calculate enrichment success rate."""
        if self.enrichment_attempts == 0:
            return 0.0
        return self.enrichment_successful / self.enrichment_attempts


class PipelineMonitor:
    """Monitor pipeline execution and send alerts."""

    def __init__(self):
        self.metrics = PipelineMetrics()
        self.start_time = datetime.utcnow()
        self.pipeline_run_id: Optional[int] = None
        self._initialize_run()

    def _initialize_run(self):
        """Initialize pipeline run in database."""
        try:
            with get_db() as db:
                run = PipelineRun(
                    run_id=self.metrics.run_id,
                    start_time=self.start_time,
                    status='running'
                )
                db.add(run)
                db.commit()
                db.refresh(run)
                self.pipeline_run_id = run.id
                logger.info(f"Pipeline run initialized: {self.metrics.run_id}")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline run: {e}")

    def log_source_result(self, source: str, lead_count: int, success: bool):
        """Log results from each data source."""
        self.metrics.sources_attempted += 1
        if success:
            self.metrics.sources_successful += 1
        self.metrics.leads_by_source[source] = lead_count
        self.metrics.total_raw_leads += lead_count

        status = "✓" if success else "✗"
        logger.info(f"{status} Source '{source}': {lead_count} leads")

    def log_enrichment(self, success: bool, time_seconds: float):
        """Log enrichment attempt."""
        self.metrics.enrichment_attempts += 1
        if success:
            self.metrics.enrichment_successful += 1

        # Update average enrichment time
        if self.metrics.enrichment_attempts > 0:
            current_avg = self.metrics.avg_enrichment_time
            n = self.metrics.enrichment_attempts
            self.metrics.avg_enrichment_time = (current_avg * (n - 1) + time_seconds) / n

    def log_error(self, error: str, source: Optional[str] = None):
        """Log an error."""
        error_msg = f"{source}: {error}" if source else error
        self.metrics.errors.append(error_msg)
        logger.error(error_msg)

    def log_rate_limit(self, api: str):
        """Log API rate limit hit."""
        self.metrics.api_rate_limits_hit.append(api)
        logger.warning(f"Rate limit hit for API: {api}")

    def log_cost(self, operation: str, cost: float):
        """Log cost for an operation."""
        self.metrics.total_cost += cost
        if operation not in self.metrics.cost_by_operation:
            self.metrics.cost_by_operation[operation] = 0.0
        self.metrics.cost_by_operation[operation] += cost

    def update_lead_counts(self, new: int, updated: int, qualified: int, hot: int, warm: int, cold: int):
        """Update lead count metrics."""
        self.metrics.new_leads = new
        self.metrics.updated_leads = updated
        self.metrics.qualified_leads = qualified
        self.metrics.hot_leads = hot
        self.metrics.warm_leads = warm
        self.metrics.cold_leads = cold

    def check_health(self) -> bool:
        """
        Check if pipeline is healthy.
        Alert if:
        - Zero leads found
        - Multiple source failures
        - Enrichment success rate < 50%
        - Unusual score distribution
        """
        alerts = []

        if self.metrics.total_raw_leads == 0:
            alerts.append("🚨 CRITICAL: Zero leads collected from all sources")

        if self.metrics.sources_attempted > 0:
            success_rate = self.metrics.sources_successful / self.metrics.sources_attempted
            if success_rate < 0.5:
                alerts.append(
                    f"⚠️ WARNING: Only {self.metrics.sources_successful}/{self.metrics.sources_attempted} "
                    f"sources succeeded ({success_rate:.1%})"
                )

        if self.metrics.enrichment_attempts > 0 and self.metrics.enrichment_success_rate < 0.5:
            alerts.append(
                f"⚠️ WARNING: Low enrichment success rate: {self.metrics.enrichment_success_rate:.1%}"
            )

        if self.metrics.total_raw_leads > 0 and self.metrics.qualified_leads == 0:
            alerts.append("⚠️ WARNING: Zero qualified leads (all below threshold)")

        if len(self.metrics.api_rate_limits_hit) > 0:
            apis = ", ".join(self.metrics.api_rate_limits_hit)
            alerts.append(f"⚠️ WARNING: Rate limits hit for: {apis}")

        # Check cost against budget
        if settings.enable_cost_alerts and self.metrics.total_cost > settings.monthly_budget:
            alerts.append(
                f"💰 ALERT: Cost ${self.metrics.total_cost:.2f} exceeds budget "
                f"${settings.monthly_budget:.2f}"
            )

        if alerts:
            self.send_alerts(alerts)
            return False

        return True

    def send_alerts(self, alerts: List[str]):
        """Send alerts via Slack."""
        if not settings.slack_webhook_url:
            logger.warning("Slack webhook not configured, alerts not sent")
            for alert in alerts:
                logger.warning(alert)
            return

        try:
            message = {
                'text': f"*Sourcing Pipeline Alerts* - {self.metrics.run_date.strftime('%Y-%m-%d %H:%M')}\n\n" +
                        "\n".join(f"• {a}" for a in alerts)
            }
            response = requests.post(settings.slack_webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logger.info("Alerts sent to Slack successfully")
        except Exception as e:
            logger.error(f"Failed to send Slack alerts: {e}")

    def complete(self, status: str = 'completed'):
        """Mark pipeline run as complete and save metrics."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        try:
            with get_db() as db:
                if self.pipeline_run_id:
                    run = db.query(PipelineRun).filter(PipelineRun.id == self.pipeline_run_id).first()
                    if run:
                        run.end_time = end_time
                        run.duration_seconds = duration
                        run.status = status
                        run.sources_attempted = self.metrics.sources_attempted
                        run.sources_successful = self.metrics.sources_successful
                        run.total_raw_leads = self.metrics.total_raw_leads
                        run.new_leads = self.metrics.new_leads
                        run.updated_leads = self.metrics.updated_leads
                        run.qualified_leads = self.metrics.qualified_leads
                        run.metrics = {
                            'leads_by_source': self.metrics.leads_by_source,
                            'hot_leads': self.metrics.hot_leads,
                            'warm_leads': self.metrics.warm_leads,
                            'cold_leads': self.metrics.cold_leads,
                            'enrichment_success_rate': self.metrics.enrichment_success_rate,
                            'total_cost': self.metrics.total_cost,
                            'cost_by_operation': self.metrics.cost_by_operation,
                        }
                        run.errors = self.metrics.errors
                        db.commit()

            logger.info(f"Pipeline run completed: {status} (duration: {duration:.1f}s)")

            # Check health and send summary
            self.check_health()
            report = self.generate_report()
            logger.info(f"\n{report}")

            # Send success summary to Slack if configured
            if settings.slack_webhook_url and status == 'completed':
                self._send_success_summary()

        except Exception as e:
            logger.error(f"Failed to complete pipeline run: {e}")

    def _send_success_summary(self):
        """Send success summary to Slack."""
        try:
            message = {
                'text': self.generate_report()
            }
            response = requests.post(settings.slack_webhook_url, json=message, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send success summary: {e}")

    def format_leads_by_source(self) -> str:
        """Format leads by source for reporting."""
        lines = []
        for source, count in sorted(self.metrics.leads_by_source.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  - {source}: {count} leads")
        return "\n".join(lines) if lines else "  No leads collected"

    def format_errors(self) -> str:
        """Format errors for reporting."""
        if not self.metrics.errors:
            return "  None"
        return "\n".join(f"  - {e}" for e in self.metrics.errors[:10])  # Limit to 10 errors

    def format_costs(self) -> str:
        """Format costs by operation."""
        lines = []
        for operation, cost in sorted(self.metrics.cost_by_operation.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  - {operation}: ${cost:.2f}")
        return "\n".join(lines) if lines else "  No costs incurred"

    def generate_report(self) -> str:
        """Generate weekly summary report."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        return f"""
╔══════════════════════════════════════════════════════════════════╗
║            Sourcing Pipeline Report                              ║
║            {self.metrics.run_date.strftime('%Y-%m-%d %H:%M:%S UTC')}                           ║
╚══════════════════════════════════════════════════════════════════╝

📊 COLLECTION:
  • Sources attempted: {self.metrics.sources_attempted}
  • Sources successful: {self.metrics.sources_successful}
  • Total raw leads: {self.metrics.total_raw_leads}
  • Duration: {duration:.1f}s

  Leads by source:
{self.format_leads_by_source()}

🎯 QUALIFIED LEADS:
  • Total qualified: {self.metrics.qualified_leads} (score >= {settings.min_score_threshold})
  • Hot leads: {self.metrics.hot_leads} (immediate outreach)
  • Warm leads: {self.metrics.warm_leads} (nurture campaign)
  • Cold leads: {self.metrics.cold_leads} (watch list)

📈 PROCESSING:
  • New leads: {self.metrics.new_leads}
  • Updated existing: {self.metrics.updated_leads}
  • Duplicates removed: {self.metrics.duplicates_found}
  • Enrichment success: {self.metrics.enrichment_success_rate:.1%} ({self.metrics.enrichment_successful}/{self.metrics.enrichment_attempts})

💰 COSTS:
  • Total: ${self.metrics.total_cost:.2f}
  • Budget: ${settings.monthly_budget:.2f}
  • Remaining: ${settings.monthly_budget - self.metrics.total_cost:.2f}

  Costs by operation:
{self.format_costs()}

⚠️ ISSUES:
{self.format_errors()}

{'─' * 66}
        """.strip()
