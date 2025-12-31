# Ellipsis Venture: AI Deep Tech Founder Sourcing Engine

**Automated weekly pipeline to identify pre-seed AI deep tech founders in Europe before they raise.**

## 🎯 Overview

This system automatically identifies high-potential AI Deep Tech founders at the earliest stages (pre-seed, stealth, considering founding) across European hubs. It aggregates data from academic publications, GitHub activity, university spin-offs, EU research grants, and more to produce a ranked, segmented list of leads for outreach.

### Key Features

- **📊 Multi-Source Data Collection**: ArXiv, GitHub, EU Grants, Conferences
- **🎯 Advanced Scoring**: Multi-signal momentum detection, negative signal filtering
- **🔥 Readiness Assessment**: Categorizes leads as HOT/WARM/COLD for prioritized outreach
- **💰 Cost Tracking**: Smart enrichment strategy stays within budget
- **📈 Continuous Learning**: Feedback loop improves scoring over time
- **🗄️ Historical Tracking**: Never re-contact the same person

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python -c "from pipeline.database import init_db; init_db()"

# Run pipeline
python -m pipeline.main
```

## 📊 Expected Results (Phase 1)

- **~100-150 leads/month** from ArXiv + EU Grants
- **~50-75 qualified leads** (score >= 6.0)
- **~15-25 HOT leads** for immediate outreach

## 📝 Documentation

- **Comprehensive Plan Review**: `plan_review_and_improvements.md`
- **Setup Guide**: See Quick Start above

**Built with ❤️ for Ellipsis Venture**
