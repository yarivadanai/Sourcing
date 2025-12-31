"""Configuration settings for the sourcing engine."""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/sourcing_engine",
        alias="DATABASE_URL"
    )

    # API Keys
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    proxycurl_api_key: Optional[str] = Field(default=None, alias="PROXYCURL_API_KEY")
    hunter_io_api_key: Optional[str] = Field(default=None, alias="HUNTER_IO_API_KEY")
    twitter_bearer_token: Optional[str] = Field(default=None, alias="TWITTER_BEARER_TOKEN")
    crunchbase_api_key: Optional[str] = Field(default=None, alias="CRUNCHBASE_API_KEY")

    # Airtable
    airtable_api_key: Optional[str] = Field(default=None, alias="AIRTABLE_API_KEY")
    airtable_base_id: Optional[str] = Field(default=None, alias="AIRTABLE_BASE_ID")
    airtable_table_name: str = Field(default="Leads", alias="AIRTABLE_TABLE_NAME")
    airtable_enabled: bool = Field(default=False)

    # Monitoring
    slack_webhook_url: Optional[str] = Field(default=None, alias="SLACK_WEBHOOK_URL")
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")

    # Cost Management
    monthly_budget: float = Field(default=150.0, alias="MONTHLY_BUDGET")
    enable_cost_alerts: bool = Field(default=True, alias="ENABLE_COST_ALERTS")

    # Pipeline Configuration
    min_score_threshold: float = Field(default=6.0, alias="MIN_SCORE_THRESHOLD")
    days_back_arxiv: int = Field(default=7, alias="DAYS_BACK_ARXIV")
    enable_smart_enrichment: bool = Field(default=True, alias="ENABLE_SMART_ENRICHMENT")

    # Target Geography
    target_countries: List[str] = Field(
        default=["Switzerland", "UK", "Germany", "Sweden", "France", "Netherlands", "Belgium"]
    )
    target_cities: List[str] = Field(
        default=[
            "zurich", "switzerland", "london", "uk", "united kingdom",
            "berlin", "germany", "munich", "stockholm", "sweden",
            "paris", "france", "amsterdam", "netherlands", "brussels",
            "belgium", "oxford", "cambridge", "edinburgh", "delft", "eindhoven"
        ]
    )

    # Target Universities (Tier 1)
    tier_1_universities: List[str] = Field(
        default=[
            "ETH Zurich", "EPFL", "Oxford", "Cambridge", "Imperial College",
            "TUM", "KTH", "University of Amsterdam", "UCL"
        ]
    )

    # Target Universities (Tier 2)
    tier_2_universities: List[str] = Field(
        default=[
            "TU Delft", "RWTH Aachen", "TU Berlin", "Edinburgh", "Manchester",
            "Sorbonne", "ENS Paris", "Max Planck Institute", "LMU Munich"
        ]
    )

    # AI Topics for filtering
    ai_topics: List[str] = Field(
        default=[
            "machine-learning", "deep-learning", "pytorch", "transformers",
            "llm", "langchain", "diffusion", "robotics", "computer-vision",
            "nlp", "reinforcement-learning", "agents", "rag", "foundation-models"
        ]
    )

    # ArXiv categories
    arxiv_categories: List[str] = Field(
        default=["cs.AI", "cs.LG", "cs.CV", "cs.RO", "cs.CL", "cs.HC"]
    )

    # Enrichment thresholds
    enrichment_linkedin_basic_threshold: float = 5.0
    enrichment_linkedin_full_threshold: float = 7.0
    enrichment_email_threshold: float = 7.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
