# Ellipsis Venture: AI Deep Tech Founder Sourcing Engine

**Automated pipeline to identify pre-seed AI deep tech founders in Europe before they raise.**

## 🎯 Overview

This system automatically identifies high-potential AI Deep Tech founders at the earliest stages (pre-seed, stealth, considering founding) across European hubs. It aggregates data from 10 comprehensive sources including academic publications, GitHub activity, university spin-offs, EU research grants, conferences, hackathons, patents, Twitter, and technical blogs to produce a ranked, segmented list of leads for outreach.

### Key Innovation: Multi-Signal Momentum Scoring

The system's core advantage is detecting founders appearing across **multiple signals** within weeks:
- Published ArXiv paper → Speaking at conference → GitHub trending → **+30 bonus points**
- Won hackathon → Tweeting about startup → EU grant recipient → **+20 bonus points**

This "momentum detection" identifies founders at their inflection point—precisely when they're considering founding.

## ✨ Key Features

### Data Collection (10 Sources)

- **📚 Academic**: ArXiv papers, Conference speakers (NeurIPS, ICML, ICLR, CVPR, ECCV, EMNLP, ACL, ECAI)
- **💻 Technical**: GitHub trending repos, Technical blogs (Medium, Substack), Patents (EPO)
- **🏫 Institutional**: 40 university spin-offs (Switzerland, UK, Sweden, Germany, Netherlands, France, Belgium, Denmark, Norway, Austria)
- **🚀 Startup Ecosystem**: 22 accelerators (EF, Techstars, Antler, etc.), Hackathon winners (Devpost, MLH)
- **💰 Funding**: EU Grants (CORDIS), Research funding databases
- **🐦 Social Signals**: Twitter/X academic monitoring, building in public threads

### Intelligence Layer

- **🎯 Multi-Signal Momentum Detection**: +10/+20/+30 bonus for cross-source appearances
- **🔥 Readiness Assessment**: HOT (ready to contact) / WARM (nurture) / COLD (monitor)
- **⚡ Negative Signal Filtering**: Removes Series A+ founders, big tech employees
- **🎓 Network Effects Scoring**: Bonus for successful lab affiliations

### Enrichment & CRM

- **💼 LinkedIn Enrichment**: Smart Proxycurl integration (only high-scoring leads)
- **📧 Email Finding**: Hunter.io with verification
- **📊 Airtable Integration**: Automatic CRM sync with outreach hooks
- **📈 Analytics & Feedback Loop**: Track performance, optimize scoring

### Cost Management

- **💰 Smart Budget Optimization**: Score >= 7.5 gets full enrichment, 5.0-7.4 gets basic
- **📉 Cost Tracking**: Real-time monitoring with alerts at 80% budget
- **🎚️ Configurable Thresholds**: Adjust enrichment strategy based on budget

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys (see SETUP.md for details)

# Initialize database
python -c "from pipeline.database import init_db; init_db()"

# Run pipeline
python -m pipeline.main
```

**For detailed setup instructions**, see [SETUP.md](SETUP.md).

## 🛠️ Utility Tools

### Pipeline Validation

Validate the pipeline end-to-end and check lead quality:

```bash
python scripts/validate_pipeline.py
```

This will:
- Run the pipeline with recent data
- Validate lead quality against Ellipsis Venture criteria
- Check European focus, AI/Deep Tech relevance, data completeness
- Generate a quality report with sample leads

### Historical Data Backfill

Pre-fill the database with historical data from Q4 2025:

```bash
# Dry run (see what would be collected)
python scripts/backfill_historical.py --quarter Q4_2025 --dry-run

# Execute backfill
python scripts/backfill_historical.py --quarter Q4_2025
```

This collects data from October-December 2025 in weekly chunks to build a rich historical dataset.

### Personalized Outreach Messages

Generate customized outreach messages for leads:

```bash
# Generate for a single lead
python scripts/generate_outreach.py --lead-id 123 --sender-name "Your Name"
python scripts/generate_outreach.py --email john@example.com
python scripts/generate_outreach.py --lead-name "John Doe"

# LinkedIn connection message (300 char limit)
python scripts/generate_outreach.py --lead-id 123 --linkedin

# Use specific template
python scripts/generate_outreach.py --lead-id 123 --template arxiv_paper

# Copy to clipboard
python scripts/generate_outreach.py --lead-id 123 --copy

# Batch generate for CSV
python scripts/generate_outreach.py --batch output/hot_leads.csv --sender-name "Your Name"

# List available templates
python scripts/generate_outreach.py --list-templates
```

**Available Templates:**
- `arxiv_paper` - For researchers with recent papers
- `conference_speaker` - For conference presenters
- `github_project` - For GitHub projects
- `hackathon_winner` - For hackathon winners
- `eu_grant` - For ERC/EU grant recipients
- `university_spinoff` - For university researchers
- `accelerator` - For accelerator participants
- `twitter_building` - For "building in public" founders
- `multi_signal` - For leads with 3+ signals (momentum)
- `generic` - Fallback template

Messages are automatically personalized with:
- Lead's latest activity (paper, project, talk, etc.)
- Specific technical details from their work
- Context-aware hooks based on readiness (HOT/WARM/COLD)
- European/AI focus alignment

## 📊 Expected Results

### Full Pipeline (All 10 Sources)

- **~500-800 raw leads/month**
- **~200-300 qualified leads** (score >= 5.0)
- **~50-75 HOT leads** (score >= 7.5, ready for immediate outreach)
- **~100-150 WARM leads** (score 6.0-7.4, nurture campaigns)

### Lead Quality Indicators

**HOT Leads** (Score >= 7.5):
- Multiple signals within 30 days
- Recent activity (paper + code + conference)
- Clear technical expertise
- Pre-seed or considering founding
- European location

**WARM Leads** (Score 6.0-7.4):
- 2+ signals
- Strong technical background
- Potentially exploring founding
- Worth nurturing

**COLD Leads** (Score 5.0-5.9):
- Single strong signal
- Monitor for momentum
- Low-touch campaigns

## 🗺️ Geographic Coverage

### 40 European Universities

- **Switzerland (4)**: ETH Zurich, EPFL, University of Zurich, University of Basel
- **UK (8)**: Oxford, Cambridge, Imperial, UCL, Edinburgh, King's College, Manchester, Warwick
- **Sweden (4)**: KTH, Chalmers, Lund, Uppsala
- **Germany (7)**: TUM, LMU Munich, RWTH Aachen, Heidelberg, HU Berlin, Karlsruhe, Stuttgart
- **Netherlands (4)**: TU Delft, University of Amsterdam, TU Eindhoven, Utrecht
- **France (4)**: École Polytechnique, Sorbonne, PSL, Grenoble INP
- **Belgium (1)**: KU Leuven
- **Denmark (1)**: DTU
- **Norway (1)**: NTNU
- **Austria (1)**: TU Wien

### 22 European Accelerators

Entrepreneurs First, Techstars, Antler, Startup Wise Guys, Seedcamp, HEARTFELT_, Rockstart, NDRC, Plug and Play, imec.istart, Founders Factory, Startupbootcamp, Bethnal Green Ventures, Wayra, Birdhouse, Accelerace, Sting, Tenity, Demium, LVenture Group, HighTechXL, Norrsken Evolve

## 💰 Cost Structure

### Budget-Friendly Tiers

**Free Tier** (8/10 sources, $0/month):
- ArXiv, EU Grants, GitHub, Conferences, Universities, Accelerators, Hackathons, Blogs
- **~300-400 leads/month**, no enrichment
- Great for testing and validation

**Starter** ($150/month):
- All free sources + LinkedIn (basic) + Email finding
- **~200 qualified + enriched leads/month**
- 50 HOT leads with emails

**Professional** ($300/month):
- All sources + full LinkedIn + Email + Twitter monitoring
- **~250 qualified + enriched leads/month**
- 75 HOT leads with full profiles

### API Cost Breakdown

| Service | Monthly Cost | Usage | Purpose |
|---------|-------------|-------|---------|
| Twitter API | $100 | 10K tweets | Academic monitoring |
| Proxycurl (LinkedIn) | $100-150 | 3K-5K profiles | Profile enrichment |
| Hunter.io (Email) | $50-100 | 1K-2K emails | Email finding |
| **Total** | **$250-350** | | |

**Smart enrichment strategy** ensures you only pay for high-quality leads (score >= 5.0).

## 📂 Output Files

```
output/
├── hot_leads.csv          # Score >= 7.5 (ready to contact NOW)
├── warm_leads.csv         # Score 6.0-7.4 (nurture campaigns)
├── cold_leads.csv         # Score 5.0-5.9 (monitor for signals)
├── all_leads.csv          # All qualified leads
└── pipeline_report.json   # Execution summary and analytics
```

### CSV Format

Each lead includes:
- **Contact**: Name, email, LinkedIn URL
- **Context**: University, company, current role
- **Scoring**: Total score, momentum score, readiness (HOT/WARM/COLD)
- **Attribution**: Sources found, timestamps, recency
- **Outreach**: AI-generated outreach hook based on latest activity

### Airtable Integration

Automatic CRM sync with:
- Deduplication by email/LinkedIn/name
- Status tracking (New → Contacted → Responded → Meeting → Passed)
- Outreach history
- Score and readiness fields
- Source attribution

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  ArXiv   │  GitHub  │ EU Grants│Conferences│  Universities   │
│  Papers  │ Trending │  CORDIS  │ Speakers  │   Spin-offs     │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│Accelerators│Hackathons│ Patents │ Twitter  │  Tech Blogs     │
│  22 Accs │Devpost/MLH│   EPO   │ Academic │ Medium/Substack │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Deduplication & Enrichment Layer                │
│  • Fuzzy name matching (85% threshold)                       │
│  • Smart LinkedIn enrichment (score >= 5.0)                  │
│  • Email finding (score >= 7.5)                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Scoring & Assessment Layer                  │
│  • Multi-signal momentum (+10/+20/+30)                       │
│  • Negative signal filtering (big tech, late stage)          │
│  • Network effects (successful lab bonus)                    │
│  • Readiness assessment (HOT/WARM/COLD)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Output & CRM Layer                        │
│  • Segmented CSV files (hot/warm/cold)                       │
│  • Airtable CRM sync                                         │
│  • Outreach hooks generation                                 │
│  • Analytics and reporting                                   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Tech Stack

- **Language**: Python 3.11+
- **Database**: PostgreSQL 14+ (historical tracking, deduplication)
- **Data Models**: Pydantic for validation, SQLAlchemy ORM
- **Web Scraping**: BeautifulSoup4, requests
- **APIs**: ArXiv, GitHub, CORDIS, Proxycurl, Hunter.io, Twitter, Airtable
- **Monitoring**: Loguru logging, Slack webhooks
- **Deployment**: Docker, systemd timers, cron

## 📈 Analytics & Optimization

### Built-in Analytics

```bash
# Generate 30-day performance report
python -m pipeline.analytics report --days 30

# Source performance breakdown
python -m pipeline.analytics sources

# Scoring effectiveness analysis
python -m pipeline.analytics scoring

# Current spend tracking
python -m pipeline.analytics current-spend
```

### Feedback Loop

Track outreach performance to improve scoring:

```bash
# Record outreach attempt
python -m pipeline.analytics record-outreach \
  --lead-id 123 --method email

# Record response
python -m pipeline.analytics record-response \
  --lead-id 123 --responded true --meeting-scheduled true

# Generate insights
python -m pipeline.analytics insights
```

The system automatically adjusts scoring weights based on what leads to successful meetings.

## 🔒 Security & Privacy

- All API keys in environment variables (never committed)
- PostgreSQL with user-level permissions
- GDPR-compliant data handling (EU-focused)
- Opt-out mechanism for leads
- Secure credential storage
- Regular dependency updates

## 📚 Documentation

- **[SETUP.md](SETUP.md)**: Complete setup and deployment guide
- **[plan_review_and_improvements.md](plan_review_and_improvements.md)**: Original plan and enhancement recommendations
- **[pipeline/](pipeline/)**: Source code with inline documentation

## 🛠️ Development

### Project Structure

```
sourcing-engine/
├── config/
│   └── settings.py          # Pydantic configuration
├── pipeline/
│   ├── sources/             # 10 data sources
│   │   ├── arxiv_source.py
│   │   ├── github_source.py
│   │   ├── eu_grants_source.py
│   │   ├── conference_source.py
│   │   ├── university_spinoffs_source.py
│   │   ├── accelerator_source.py
│   │   ├── hackathon_source.py
│   │   ├── patent_source.py
│   │   ├── twitter_source.py
│   │   └── blog_source.py
│   ├── enrichment/          # LinkedIn + Email
│   │   ├── linkedin.py
│   │   └── email.py
│   ├── scoring/             # Scoring engine
│   │   ├── engine.py
│   │   └── readiness.py
│   ├── output/              # Export modules
│   │   └── airtable_exporter.py
│   ├── models.py            # Database models
│   ├── database.py          # DB connection
│   ├── monitoring.py        # Alerts & monitoring
│   ├── cost_tracker.py      # Budget tracking
│   ├── analytics.py         # Analytics & feedback
│   └── main.py              # Pipeline orchestration
├── SETUP.md                 # Setup guide
└── README.md                # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pipeline

# Run specific test
pytest tests/test_scoring.py
```

## 🤝 Contributing

This is a private project for Ellipsis Venture. For questions or issues, contact the development team.

## 📄 License

Proprietary - Ellipsis Venture

---

**Built with ❤️ for Ellipsis Venture**

*Identifying Europe's next generation of AI deep tech founders, before they raise.*
