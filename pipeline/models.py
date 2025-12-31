"""SQLAlchemy models for the sourcing engine."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, JSON, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from pipeline.database import Base


class Lead(Base):
    """Main lead model representing a potential founder."""

    __tablename__ = "leads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Core identity
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), unique=True, index=True)

    # Contact information
    email = Column(String(255))
    linkedin_url = Column(String(500))
    twitter_handle = Column(String(100))
    github_profile = Column(String(500))
    personal_website = Column(String(500))

    # Professional information
    university_affiliation = Column(String(255))
    company_name = Column(String(255))
    company_website = Column(String(500))
    current_position = Column(String(255))

    # Location
    location = Column(String(255))
    country = Column(String(100))

    # Scoring
    total_score = Column(Float, default=0.0, index=True)
    preliminary_score = Column(Float, default=0.0)
    momentum_score = Column(Float, default=0.0)
    network_score = Column(Float, default=0.0)
    negative_signal_penalty = Column(Float, default=0.0)

    # Readiness assessment
    readiness = Column(String(20), index=True)  # hot, warm, cold
    readiness_signals = Column(JSON)  # List of signals that determined readiness

    # Metadata
    first_seen_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default='new', index=True)  # new, contacted, responded, qualified, disqualified

    # Source tracking
    source_count = Column(Integer, default=1)  # Number of different sources
    primary_source = Column(String(50))  # First source that found this lead

    # Outreach tracking
    contacted_count = Column(Integer, default=0)
    last_contacted = Column(DateTime, nullable=True)
    responded = Column(Boolean, default=False)
    meeting_scheduled = Column(Boolean, default=False)

    # Enrichment data
    background = Column(Text)  # Generated background summary
    outreach_hook = Column(Text)  # Generated personalized hook
    enrichment_data = Column(JSON)  # Additional enrichment data

    # Relationships
    sources = relationship("LeadSource", back_populates="lead", cascade="all, delete-orphan")
    outreach_history = relationship("OutreachHistory", back_populates="lead", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_status_score', 'status', 'total_score'),
        Index('idx_readiness_score', 'readiness', 'total_score'),
    )

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.name}', score={self.total_score}, status='{self.status}')>"


class LeadSource(Base):
    """Track which sources discovered each lead."""

    __tablename__ = "lead_sources"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False, index=True)

    # Source information
    source = Column(String(50), nullable=False, index=True)  # arxiv, github, spinoff, etc.
    source_url = Column(String(500))
    discovered_date = Column(DateTime, default=datetime.utcnow)

    # Raw data from this source
    raw_data = Column(JSON)

    # Scoring contribution from this source
    score_contribution = Column(Float, default=0.0)

    # Relationship
    lead = relationship("Lead", back_populates="sources")

    def __repr__(self):
        return f"<LeadSource(lead_id={self.lead_id}, source='{self.source}')>"


class OutreachHistory(Base):
    """Track outreach attempts and responses."""

    __tablename__ = "outreach_history"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False, index=True)

    # Outreach details
    contacted_date = Column(DateTime, default=datetime.utcnow)
    method = Column(String(50))  # email, linkedin, twitter
    message_content = Column(Text)

    # Response tracking
    responded = Column(Boolean, default=False)
    response_date = Column(DateTime, nullable=True)
    response_content = Column(Text, nullable=True)

    # Outcome
    meeting_scheduled = Column(Boolean, default=False)
    meeting_date = Column(DateTime, nullable=True)
    outcome = Column(String(50))  # interested, not_interested, no_response, qualified

    # Notes
    notes = Column(Text)

    # Relationship
    lead = relationship("Lead", back_populates="outreach_history")

    def __repr__(self):
        return f"<OutreachHistory(lead_id={self.lead_id}, method='{self.method}', responded={self.responded})>"


class CostLog(Base):
    """Track API and service costs."""

    __tablename__ = "cost_log"

    id = Column(Integer, primary_key=True, index=True)

    # Cost details
    date = Column(DateTime, default=datetime.utcnow, index=True)
    operation = Column(String(100), nullable=False)  # linkedin_basic, linkedin_full, email_finding, etc.
    service = Column(String(100))  # proxycurl, hunter.io, etc.
    cost = Column(Float, nullable=False)

    # Context
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='SET NULL'), nullable=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='SET NULL'), nullable=True)

    # Metadata
    success = Column(Boolean, default=True)
    notes = Column(Text)

    def __repr__(self):
        return f"<CostLog(operation='{self.operation}', cost=${self.cost:.2f})>"


class PipelineRun(Base):
    """Track pipeline execution runs."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), unique=True, nullable=False, index=True)

    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Status
    status = Column(String(50), default='running')  # running, completed, failed

    # Metrics (stored as JSON for flexibility)
    metrics = Column(JSON)

    # Sources attempted/successful
    sources_attempted = Column(Integer, default=0)
    sources_successful = Column(Integer, default=0)

    # Lead counts
    total_raw_leads = Column(Integer, default=0)
    new_leads = Column(Integer, default=0)
    updated_leads = Column(Integer, default=0)
    qualified_leads = Column(Integer, default=0)

    # Errors
    errors = Column(JSON)

    def __repr__(self):
        return f"<PipelineRun(id='{self.run_id}', status='{self.status}')>"
