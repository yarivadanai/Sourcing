"""Base class for data sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class RawLead:
    """Raw lead data from a source before database insertion."""

    name: str
    source: str
    raw_data: Dict[str, Any]

    # Optional fields
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_profile: Optional[str] = None
    twitter_handle: Optional[str] = None
    university_affiliation: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    location: Optional[str] = None
    source_url: Optional[str] = None


class BaseSource(ABC):
    """Base class for all data sources."""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logger.bind(source=source_name)

    @abstractmethod
    def collect(self) -> List[RawLead]:
        """
        Collect leads from this source.

        Returns:
            List of RawLead objects
        """
        pass

    def is_european_affiliation(self, affiliation: Optional[str], tier_1_unis: List[str], tier_2_unis: List[str]) -> bool:
        """Check if affiliation is from a target European institution."""
        if not affiliation:
            return False

        affiliation_lower = affiliation.lower()
        all_unis = tier_1_unis + tier_2_unis

        return any(uni.lower() in affiliation_lower for uni in all_unis)

    def is_european_location(self, location: Optional[str], target_cities: List[str]) -> bool:
        """Check if location matches European target locations."""
        if not location:
            return False

        location_lower = location.lower()
        return any(city in location_lower for city in target_cities)

    def extract_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Extract matching keywords from text."""
        if not text:
            return []

        text_lower = text.lower()
        return [kw for kw in keywords if kw in text_lower]

    def log_result(self, lead_count: int, success: bool = True):
        """Log collection result."""
        if success:
            self.logger.info(f"Collected {lead_count} leads")
        else:
            self.logger.error(f"Collection failed")
