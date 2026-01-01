# Setup and Deployment Guide

Complete guide for setting up and deploying the AI Deep Tech Founder Sourcing Engine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Database Setup](#database-setup)
3. [Environment Configuration](#environment-configuration)
4. [API Keys and Services](#api-keys-and-services)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the Pipeline](#running-the-pipeline)
8. [Docker Deployment](#docker-deployment)
9. [Monitoring and Alerts](#monitoring-and-alerts)
10. [Cost Management](#cost-management)
11. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git
- Docker and Docker Compose (optional, for containerized deployment)

## Database Setup

### Local PostgreSQL Installation

**macOS (using Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Create Database:**
```bash
# Connect as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE sourcing_engine;
CREATE USER sourcing_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE sourcing_engine TO sourcing_user;
\q
```

### Verify Connection

```bash
psql -h localhost -U sourcing_user -d sourcing_engine
```

## Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://sourcing_user:your_secure_password@localhost:5432/sourcing_engine

# ArXiv (No API key needed)
ARXIV_ENABLED=true

# EU Grants - CORDIS (No API key needed)
EU_GRANTS_ENABLED=true

# GitHub
GITHUB_ENABLED=true
GITHUB_TOKEN=ghp_your_github_token_here

# Conferences (Web scraping - no keys needed)
CONFERENCES_ENABLED=true

# University Spin-offs (Web scraping - no keys needed)
UNIVERSITY_SPINOFFS_ENABLED=true

# Accelerators (Web scraping - no keys needed)
ACCELERATORS_ENABLED=true

# Hackathons (Devpost, MLH - no keys needed)
HACKATHONS_ENABLED=true

# Patents (EPO - optional, requires registration)
PATENTS_ENABLED=false
EPO_API_KEY=your_epo_api_key
EPO_API_SECRET=your_epo_api_secret

# Twitter/X
TWITTER_ENABLED=true
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Technical Blogs (Web scraping - no keys needed)
BLOGS_ENABLED=true

# LinkedIn Enrichment (Proxycurl)
LINKEDIN_ENABLED=true
PROXYCURL_API_KEY=your_proxycurl_api_key

# Email Finding (Hunter.io)
EMAIL_FINDING_ENABLED=true
HUNTER_IO_API_KEY=your_hunter_io_api_key

# Airtable CRM
AIRTABLE_ENABLED=true
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_NAME=Leads

# Monitoring
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ENABLE_SLACK_ALERTS=true

# Cost Tracking
MONTHLY_BUDGET_USD=300
COST_ALERT_THRESHOLD=0.8

# Scoring
MIN_SCORE_THRESHOLD=5.0
HOT_LEAD_THRESHOLD=7.5

# Output
OUTPUT_DIR=./output
```

## API Keys and Services

### Required Services

#### 1. GitHub Token (Free)
- Go to https://github.com/settings/tokens
- Generate new token (classic)
- Select scopes: `public_repo`, `read:user`
- Copy token to `.env`

#### 2. Proxycurl (LinkedIn Enrichment)
- Sign up at https://nubela.co/proxycurl/
- Plans start at $99/month
- Get API key from dashboard
- **Cost**: ~$0.01-0.03 per profile
- Budget: ~3,000-10,000 profiles/month at $300 budget

#### 3. Hunter.io (Email Finding)
- Sign up at https://hunter.io/
- Plans start at $49/month (1,000 searches)
- Get API key from dashboard
- **Cost**: ~$0.05 per email search
- Budget: ~1,000-2,000 emails/month

#### 4. Twitter API (Optional but Recommended)
- Apply at https://developer.twitter.com/
- Essential plan: $100/month (10K tweets/month)
- Get Bearer Token
- **Cost**: $100/month fixed
- Budget: Included in monthly cost

### Optional Services

#### 5. European Patent Office API (Optional)
- Register at https://developers.epo.org/
- Free for non-commercial use
- OAuth credentials required
- **Cost**: Free

#### 6. Airtable (CRM)
- Sign up at https://airtable.com/
- Free tier: 1,200 records
- Plus: $20/user/month (50,000 records)
- Get API key from https://airtable.com/account
- **Cost**: Free to $20/month

#### 7. Slack (Monitoring)
- Create webhook at https://api.slack.com/messaging/webhooks
- Free
- **Cost**: Free

### Minimum Setup (Budget-Conscious)

You can start with just **free data sources**:

```env
# Free sources only
ARXIV_ENABLED=true
EU_GRANTS_ENABLED=true
GITHUB_ENABLED=true
CONFERENCES_ENABLED=true
UNIVERSITY_SPINOFFS_ENABLED=true
ACCELERATORS_ENABLED=true
HACKATHONS_ENABLED=true
BLOGS_ENABLED=true

# Disable paid services
LINKEDIN_ENABLED=false
EMAIL_FINDING_ENABLED=false
TWITTER_ENABLED=false
PATENTS_ENABLED=false
AIRTABLE_ENABLED=false
```

This gives you 8/10 data sources with **zero monthly cost**.

## Installation

### Clone Repository

```bash
git clone https://github.com/your-org/sourcing-engine.git
cd sourcing-engine
```

### Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Initialize Database

```bash
# Run migrations
python -m alembic upgrade head

# Or use the setup script
python scripts/setup_database.py
```

## Configuration

### University Coverage

The engine covers **40 top European universities** across 10 countries:

- **Switzerland (4)**: ETH Zurich, EPFL, University of Zurich, University of Basel
- **UK (8)**: Oxford, Cambridge, Imperial, UCL, Edinburgh, King's College, Manchester, Warwick
- **Sweden (4)**: KTH, Chalmers, Lund, Uppsala
- **Germany (7)**: TUM, LMU, RWTH Aachen, Heidelberg, HU Berlin, Karlsruhe, Stuttgart
- **Netherlands (4)**: TU Delft, Amsterdam, Eindhoven, Utrecht
- **France (4)**: École Polytechnique, Sorbonne, PSL, Grenoble
- **Belgium (1)**: KU Leuven
- **Denmark (1)**: DTU
- **Norway (1)**: NTNU
- **Austria (1)**: TU Wien

### Accelerator Coverage

All **22 requested accelerators** are included:

1. Entrepreneurs First
2. Techstars
3. Antler
4. Startup Wise Guys
5. Seedcamp
6. HEARTFELT_
7. Rockstart
8. NDRC
9. Plug and Play Tech Center
10. imec.istart
11. Founders Factory
12. Startupbootcamp
13. Bethnal Green Ventures
14. Wayra
15. Birdhouse
16. Accelerace
17. Sting
18. Tenity
19. Demium
20. LVenture Group
21. HighTechXL
22. Norrsken Evolve

### Conference Coverage

8 major AI conferences:
- NeurIPS, ICML, ICLR, CVPR, ECCV, EMNLP, ACL, ECAI

## Running the Pipeline

### Basic Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run pipeline
python -m pipeline.main
```

### Scheduled Runs

**Using cron (Linux/macOS):**

```bash
# Edit crontab
crontab -e

# Add entry (run weekly on Monday at 9 AM)
0 9 * * 1 cd /path/to/sourcing-engine && /path/to/venv/bin/python -m pipeline.main >> /var/log/sourcing/pipeline.log 2>&1
```

**Using systemd timer (Linux):**

Create `/etc/systemd/system/sourcing-pipeline.service`:

```ini
[Unit]
Description=AI Deep Tech Sourcing Pipeline
After=network.target postgresql.service

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/sourcing-engine
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python -m pipeline.main
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/sourcing-pipeline.timer`:

```ini
[Unit]
Description=Run sourcing pipeline weekly
Requires=sourcing-pipeline.service

[Timer]
OnCalendar=Mon *-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sourcing-pipeline.timer
sudo systemctl start sourcing-pipeline.timer
```

## Docker Deployment

### Build Image

```bash
docker build -t sourcing-engine:latest .
```

### Run with Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: sourcing_engine
      POSTGRES_USER: sourcing_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sourcing_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  pipeline:
    image: sourcing-engine:latest
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://sourcing_user:your_secure_password@postgres:5432/sourcing_engine
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs

volumes:
  postgres_data:
```

Run:

```bash
docker-compose up -d
```

### Run Pipeline on Schedule

```bash
# Weekly run
docker-compose run --rm pipeline python -m pipeline.main
```

## Monitoring and Alerts

### Slack Integration

1. Create Slack webhook at https://api.slack.com/messaging/webhooks
2. Add webhook URL to `.env`:
   ```env
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ENABLE_SLACK_ALERTS=true
   ```

### Alert Types

The system sends alerts for:
- Pipeline start/completion
- Errors and failures
- Cost threshold warnings (80% of budget)
- Budget exceeded
- Low lead quality warnings
- Data source failures

### Logs

```bash
# View logs
tail -f logs/pipeline.log

# View specific run
cat logs/pipeline_2024-01-15.log
```

## Cost Management

### Budget Allocation

Example for $300/month budget:

| Service | Monthly Cost | Usage |
|---------|-------------|-------|
| Twitter API | $100 | 10K tweets |
| Proxycurl (LinkedIn) | $150 | 5,000 profiles |
| Hunter.io (Email) | $50 | 1,000 emails |
| **Total** | **$300** | |

### Smart Enrichment Strategy

The pipeline automatically optimizes costs:

- **Score >= 7.5**: Full LinkedIn profile (~$0.03) + Email finding (~$0.05)
- **Score >= 5.0**: Basic LinkedIn lookup (~$0.01)
- **Score < 5.0**: Skip enrichment

This ensures you only spend on high-quality leads.

### Cost Tracking

View cost analytics:

```bash
python -m pipeline.analytics cost-report --days 30
```

Check current spend:

```bash
python -m pipeline.analytics current-spend
```

## Output Files

The pipeline generates:

```
output/
├── hot_leads.csv          # Score >= 7.5 (ready to contact)
├── warm_leads.csv         # Score 6.0-7.4 (nurture)
├── cold_leads.csv         # Score 5.0-5.9 (monitor)
├── all_leads.csv          # All qualified leads
└── pipeline_report.json   # Execution summary
```

### CSV Format

```csv
name,email,linkedin_url,university_affiliation,company_name,total_score,momentum_score,readiness,sources,outreach_hook
John Doe,john@example.com,linkedin.com/in/johndoe,ETH Zurich,DeepAI Labs,8.5,HOT,"arxiv,github,conference","Published breakthrough paper on..."
```

### Airtable Integration

If enabled, leads are automatically synced to Airtable with:
- Automatic deduplication
- Status tracking
- Outreach hooks
- Score and readiness fields
- Source attribution

## Analytics and Feedback

### Generate Report

```bash
# 30-day performance report
python -m pipeline.analytics report --days 30

# Source performance
python -m pipeline.analytics sources

# Scoring effectiveness
python -m pipeline.analytics scoring
```

### Record Outreach

```bash
python -m pipeline.analytics record-outreach \
  --lead-id 123 \
  --method email \
  --message "Sent intro email"
```

### Record Response

```bash
python -m pipeline.analytics record-response \
  --lead-id 123 \
  --responded true \
  --meeting-scheduled true
```

### View Insights

```bash
python -m pipeline.analytics insights
```

## Troubleshooting

### Database Connection Errors

```bash
# Test connection
psql -h localhost -U sourcing_user -d sourcing_engine

# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### API Rate Limits

- **GitHub**: 5,000 requests/hour with token
- **Twitter**: 10,000 tweets/month on Essential plan
- **Proxycurl**: 300 requests/minute
- **Hunter.io**: Based on plan tier

The pipeline handles rate limits automatically with exponential backoff.

### Low Lead Quality

If you're getting low scores:

1. Check data source connectivity
2. Verify university/accelerator lists are current
3. Adjust scoring weights in `config/settings.py`
4. Review negative signals in `pipeline/scoring/engine.py`

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Install specific optional dependencies
pip install airtable-python-wrapper  # For Airtable
pip install tweepy  # For Twitter
```

### Permission Errors

```bash
# Fix output directory permissions
chmod -R 755 output/
chmod -R 755 logs/

# Fix database permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sourcing_engine TO sourcing_user;"
```

## Best Practices

### 1. Start Small

Begin with free data sources, validate the pipeline, then add paid enrichment.

### 2. Monitor Costs

Check spending weekly:
```bash
python -m pipeline.analytics current-spend
```

### 3. Tune Scoring

After first 100 leads, analyze what works:
```bash
python -m pipeline.analytics scoring
```

### 4. Regular Backups

```bash
# Backup database
pg_dump -U sourcing_user sourcing_engine > backup_$(date +%Y%m%d).sql

# Backup output
tar -czf output_backup_$(date +%Y%m%d).tar.gz output/
```

### 5. Update Regularly

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Run migrations
python -m alembic upgrade head
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/sourcing-engine/issues
- Documentation: https://github.com/your-org/sourcing-engine/wiki
- Email: support@ellipsisventure.com

## Security Notes

- Never commit `.env` file
- Rotate API keys regularly
- Use read-only database users for analytics
- Enable SSL for PostgreSQL in production
- Use environment-specific configurations
- Regularly update dependencies for security patches
