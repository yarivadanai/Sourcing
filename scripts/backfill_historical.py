"""
Historical data backfill script.

Collects data from past quarters to populate the database.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from pipeline.database import init_db
from pipeline.main import FounderSourcingPipeline


logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/backfill_{time}.log", rotation="1 week", retention="1 month", level="DEBUG")


class HistoricalBackfill:
    """Backfill historical data."""

    def __init__(self):
        self.pipeline = FounderSourcingPipeline()

    def get_q4_2025_date_ranges(self) -> List[Tuple[datetime, datetime]]:
        """
        Get date ranges for Q4 2025 (Oct, Nov, Dec).

        Returns list of (start_date, end_date) tuples for weekly chunks.
        """
        # Q4 2025: October 1 - December 31, 2025
        q4_start = datetime(2025, 10, 1)
        q4_end = datetime(2025, 12, 31)

        # Break into weekly chunks for better control
        date_ranges = []
        current_date = q4_start

        while current_date <= q4_end:
            chunk_end = min(current_date + timedelta(days=7), q4_end)
            date_ranges.append((current_date, chunk_end))
            current_date = chunk_end + timedelta(days=1)

        return date_ranges

    def backfill_date_range(self, start_date: datetime, end_date: datetime):
        """
        Backfill data for a specific date range.

        This modifies the collection logic to look at historical dates.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Backfilling: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}\n")

        # Temporarily modify settings to use historical dates
        original_lookback = settings.lookback_days

        # Calculate lookback from end_date
        days_back = (datetime.now() - end_date).days
        settings.lookback_days = days_back + 7  # Add 7 days buffer

        try:
            # Run pipeline
            leads = self.pipeline.run()
            logger.success(
                f"✓ Backfilled {len(leads)} leads for "
                f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )
            return leads

        except Exception as e:
            logger.error(f"Failed to backfill {start_date.strftime('%Y-%m-%d')}: {e}")
            return []

        finally:
            # Restore original settings
            settings.lookback_days = original_lookback

    def backfill_q4_2025(self):
        """Backfill all of Q4 2025."""
        logger.info("🔄 Starting Q4 2025 Historical Backfill")
        logger.info("=" * 60)

        # Get date ranges
        date_ranges = self.get_q4_2025_date_ranges()
        logger.info(f"Will process {len(date_ranges)} weekly chunks\n")

        total_leads = 0
        successful_chunks = 0

        for i, (start_date, end_date) in enumerate(date_ranges, 1):
            logger.info(f"\n[{i}/{len(date_ranges)}] Processing chunk...")

            leads = self.backfill_date_range(start_date, end_date)
            total_leads += len(leads)

            if leads:
                successful_chunks += 1

            # Small delay between chunks to avoid rate limits
            import time
            time.sleep(2)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Q4 2025 BACKFILL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Chunks processed: {successful_chunks}/{len(date_ranges)}")
        logger.info(f"Total leads collected: {total_leads}")
        logger.info(f"Average per chunk: {total_leads/len(date_ranges):.1f}")
        logger.success("\n✓ Q4 2025 backfill completed!")


def main():
    """Run historical backfill."""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill historical data")
    parser.add_argument(
        '--quarter',
        choices=['Q4_2025', 'Q3_2025', 'Q2_2025'],
        default='Q4_2025',
        help='Which quarter to backfill (default: Q4_2025)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - show what would be done without executing'
    )

    args = parser.parse_args()

    # Initialize database
    init_db()

    # Run backfill
    backfill = HistoricalBackfill()

    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be collected\n")
        date_ranges = backfill.get_q4_2025_date_ranges()
        logger.info(f"Would process {len(date_ranges)} chunks:")
        for i, (start, end) in enumerate(date_ranges, 1):
            logger.info(f"  {i}. {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        return 0

    if args.quarter == 'Q4_2025':
        backfill.backfill_q4_2025()
    else:
        logger.error(f"Quarter {args.quarter} not yet implemented")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
