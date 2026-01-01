"""
Personalized outreach message generator.

Creates customized cold outreach messages based on lead context.
"""

from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger

from pipeline.models import Lead
from pipeline.database import get_db
from pipeline.models import LeadSource


class OutreachMessageGenerator:
    """
    Generate personalized outreach messages for leads.

    Uses lead context (latest paper, project, conference talk, etc.)
    to create compelling, personalized messages.
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load outreach message templates."""
        return {
            'arxiv_paper': """Subject: Your recent work on {topic}

Hi {first_name},

I came across your recent paper "{paper_title}" on arXiv and was particularly impressed by {specific_insight}.

At Ellipsis Venture, we're focused on supporting technical founders building AI deep tech companies in Europe. We work with researchers like yourself who are exploring the commercial potential of their work.

{custom_hook}

Would you be open to a brief conversation about what you're working on? Even if founding isn't on your immediate radar, I'd love to learn more about your research direction.

Best,
{sender_name}
Ellipsis Venture""",

            'conference_speaker': """Subject: Saw your talk at {conference}

Hi {first_name},

I attended your presentation on "{talk_title}" at {conference} - the work on {specific_aspect} was fascinating.

I'm {sender_name} from Ellipsis Venture. We back technical founders building AI companies in Europe, particularly those coming from strong research backgrounds.

{custom_hook}

Would you be open to a quick call to discuss your research and any commercial applications you're exploring?

Best,
{sender_name}""",

            'github_project': """Subject: Impressed by {project_name}

Hi {first_name},

I discovered your work on {project_name} on GitHub. {specific_technical_detail} is a clever approach to {problem_space}.

I'm {sender_name} from Ellipsis Venture. We invest in technical founders building AI companies at the earliest stages - often before they've officially incorporated.

{custom_hook}

Would you be interested in a brief chat about what you're building and where you see it going?

Best,
{sender_name}""",

            'hackathon_winner': """Subject: Congratulations on {hackathon_name}

Hi {first_name},

Congratulations on winning {prize} at {hackathon_name} with {project_name}! The approach to {project_aspect} stood out.

I'm {sender_name} from Ellipsis Venture. We back technical founders building AI companies in Europe. Many of our portfolio companies started from hackathon projects that evolved into full companies.

{custom_hook}

Are you considering taking this further? Would love to hear what you're thinking.

Best,
{sender_name}""",

            'eu_grant': """Subject: Your ERC/EU grant on {topic}

Hi {first_name},

I saw you recently received an ERC grant for your work on {project_title}. {specific_research_aspect} addresses an important gap.

I'm {sender_name} from Ellipsis Venture. We work with researchers commercializing deep tech - several of our portfolio founders started while holding ERC grants.

{custom_hook}

Would you be open to discussing the commercial potential of your research?

Best,
{sender_name}""",

            'university_spinoff': """Subject: Your work at {university}

Hi {first_name},

I've been following the research coming out of {lab_name} at {university}, particularly your work on {research_area}.

I'm {sender_name} from Ellipsis Venture. We invest in technical founders spinning out of leading European universities - {university} has a strong track record.

{custom_hook}

Would you be interested in exploring the commercial applications of your research?

Best,
{sender_name}""",

            'accelerator': """Subject: Following your progress at {accelerator}

Hi {first_name},

I saw you're part of the current {accelerator} cohort working on {company_name}. {specific_aspect} is a compelling approach.

I'm {sender_name} from Ellipsis Venture. We often invest alongside accelerators in technical founders building AI companies.

{custom_hook}

Would you be open to a conversation about your fundraising plans?

Best,
{sender_name}""",

            'twitter_building': """Subject: Your work on {topic}

Hi {first_name},

I've been following your updates on building {product_name}. Your approach to {specific_technical_aspect} is interesting.

I'm {sender_name} from Ellipsis Venture. We back technical founders building AI companies at the earliest stages.

{custom_hook}

Would you be open to a brief call to learn more about what you're building?

Best,
{sender_name}""",

            'multi_signal': """Subject: Your work across {area_1} and {area_2}

Hi {first_name},

I've been following your work - from {signal_1} to {signal_2}. It's clear you're at an interesting inflection point with {technical_area}.

I'm {sender_name} from Ellipsis Venture. We invest in technical founders building AI companies in Europe, particularly those with strong research backgrounds and momentum.

{custom_hook}

This seems like it could be the foundation for something significant. Would you be open to discussing where you're taking this?

Best,
{sender_name}""",

            'generic': """Subject: Your work in {area}

Hi {first_name},

I came across your work in {area} and was impressed by {specific_aspect}.

I'm {sender_name} from Ellipsis Venture. We back technical founders building AI companies in Europe at the earliest stages.

{custom_hook}

Would you be open to a brief conversation about what you're working on and any commercial plans?

Best,
{sender_name}"""
        }

    def generate_message(
        self,
        lead: Lead,
        sender_name: str = "Your Name",
        custom_hook: Optional[str] = None,
        template_override: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate personalized outreach message for a lead.

        Args:
            lead: Lead object
            sender_name: Name of person sending the message
            custom_hook: Optional custom hook to add
            template_override: Optional template name to use instead of auto-selection

        Returns:
            Dict with 'subject', 'body', 'template_used', 'variables'
        """
        # Get lead sources for context
        sources = self._get_lead_sources(lead)

        # Select best template
        if template_override and template_override in self.templates:
            template_name = template_override
        else:
            template_name = self._select_best_template(lead, sources)

        # Extract variables for template
        variables = self._extract_variables(lead, sources, sender_name, custom_hook)

        # Fill template
        try:
            message = self.templates[template_name].format(**variables)

            # Extract subject line
            lines = message.strip().split('\n')
            subject = lines[0].replace('Subject: ', '').strip()
            body = '\n'.join(lines[2:]).strip()  # Skip subject and blank line

            return {
                'subject': subject,
                'body': body,
                'template_used': template_name,
                'variables': variables,
            }

        except KeyError as e:
            logger.warning(f"Missing variable {e} for template {template_name}, using generic")
            return self._generate_generic_message(lead, sender_name, custom_hook)

    def _get_lead_sources(self, lead: Lead) -> List[str]:
        """Get all sources for a lead."""
        with get_db() as db:
            sources = db.query(LeadSource).filter(
                LeadSource.lead_id == lead.id
            ).all()
            return [s.source_name for s in sources]

    def _select_best_template(self, lead: Lead, sources: List[str]) -> str:
        """
        Select best template based on lead sources and data.

        Priority:
        1. Multi-signal (if >= 3 sources)
        2. Source-specific template
        3. Generic
        """
        # Multi-signal takes precedence
        if len(sources) >= 3:
            return 'multi_signal'

        # Source-specific templates
        source_template_map = {
            'arxiv': 'arxiv_paper',
            'conference': 'conference_speaker',
            'github': 'github_project',
            'hackathon': 'hackathon_winner',
            'eu_grants': 'eu_grant',
            'university_spinoffs': 'university_spinoff',
            'accelerator': 'accelerator',
            'twitter': 'twitter_building',
        }

        # Use most recent source
        for source in sources:
            if source in source_template_map:
                return source_template_map[source]

        return 'generic'

    def _extract_variables(
        self,
        lead: Lead,
        sources: List[str],
        sender_name: str,
        custom_hook: Optional[str]
    ) -> Dict[str, str]:
        """Extract variables for template filling."""
        # Parse name
        name_parts = lead.name.split()
        first_name = name_parts[0] if name_parts else lead.name

        # Base variables
        variables = {
            'first_name': first_name,
            'full_name': lead.name,
            'sender_name': sender_name,
            'custom_hook': custom_hook or self._generate_custom_hook(lead),
        }

        # Source-specific variables
        if 'arxiv' in sources:
            # Extract from raw_data or outreach_hook
            if lead.outreach_hook:
                # Parse outreach hook for paper details
                variables.update({
                    'topic': self._extract_topic(lead),
                    'paper_title': self._extract_paper_title(lead),
                    'specific_insight': self._extract_specific_insight(lead),
                })

        if 'conference' in sources:
            variables.update({
                'conference': self._extract_conference(lead),
                'talk_title': self._extract_talk_title(lead),
                'specific_aspect': self._extract_specific_insight(lead),
            })

        if 'github' in sources:
            variables.update({
                'project_name': self._extract_project_name(lead),
                'specific_technical_detail': self._extract_technical_detail(lead),
                'problem_space': self._extract_problem_space(lead),
            })

        if 'hackathon' in sources:
            variables.update({
                'hackathon_name': self._extract_hackathon(lead),
                'prize': self._extract_prize(lead),
                'project_name': self._extract_project_name(lead),
                'project_aspect': self._extract_specific_insight(lead),
            })

        if 'eu_grants' in sources:
            variables.update({
                'topic': self._extract_topic(lead),
                'project_title': self._extract_project_title(lead),
                'specific_research_aspect': self._extract_specific_insight(lead),
            })

        if 'university_spinoffs' in sources or lead.university_affiliation:
            variables.update({
                'university': lead.university_affiliation or 'your university',
                'lab_name': self._extract_lab_name(lead),
                'research_area': self._extract_topic(lead),
            })

        if 'accelerator' in sources:
            variables.update({
                'accelerator': self._extract_accelerator(lead),
                'company_name': lead.company_name or 'your project',
                'specific_aspect': self._extract_specific_insight(lead),
            })

        if 'twitter' in sources:
            variables.update({
                'topic': self._extract_topic(lead),
                'product_name': lead.company_name or 'your project',
                'specific_technical_aspect': self._extract_technical_detail(lead),
            })

        # Multi-signal variables
        if len(sources) >= 3:
            variables.update({
                'area_1': self._extract_area_from_source(lead, sources[0]),
                'area_2': self._extract_area_from_source(lead, sources[1]),
                'signal_1': self._format_signal(sources[0]),
                'signal_2': self._format_signal(sources[1]),
                'technical_area': self._extract_topic(lead),
            })

        # Generic fallback variables
        variables.setdefault('area', self._extract_topic(lead))
        variables.setdefault('specific_aspect', 'your technical approach')

        return variables

    def _extract_topic(self, lead: Lead) -> str:
        """Extract main topic/area from lead."""
        if lead.outreach_hook:
            # Try to extract from outreach hook
            hook_lower = lead.outreach_hook.lower()
            topics = {
                'computer vision': ['computer vision', 'cv', 'image', 'vision'],
                'natural language processing': ['nlp', 'language model', 'llm', 'text'],
                'machine learning': ['machine learning', 'ml', 'neural'],
                'robotics': ['robotics', 'robot', 'autonomous'],
                'generative AI': ['generative', 'diffusion', 'gan'],
                'reinforcement learning': ['reinforcement', 'rl'],
            }

            for topic, keywords in topics.items():
                if any(kw in hook_lower for kw in keywords):
                    return topic

        return 'AI and machine learning'

    def _extract_paper_title(self, lead: Lead) -> str:
        """Extract paper title from lead data."""
        if lead.outreach_hook and 'paper' in lead.outreach_hook.lower():
            # Try to extract title from hook
            hook = lead.outreach_hook
            if '"' in hook:
                start = hook.find('"')
                end = hook.find('"', start + 1)
                if end > start:
                    return hook[start+1:end]

        return '[paper title]'

    def _extract_specific_insight(self, lead: Lead) -> str:
        """Extract a specific insight to mention."""
        if lead.outreach_hook:
            # Use part of the outreach hook
            parts = lead.outreach_hook.split('.')
            if len(parts) > 1:
                return parts[0]

        return 'the technical approach'

    def _extract_conference(self, lead: Lead) -> str:
        """Extract conference name."""
        conferences = ['NeurIPS', 'ICML', 'ICLR', 'CVPR', 'ECCV', 'EMNLP', 'ACL']
        if lead.outreach_hook:
            for conf in conferences:
                if conf.lower() in lead.outreach_hook.lower():
                    return conf
        return '[conference name]'

    def _extract_talk_title(self, lead: Lead) -> str:
        """Extract talk/presentation title."""
        return self._extract_paper_title(lead)

    def _extract_project_name(self, lead: Lead) -> str:
        """Extract project/repo name."""
        if lead.company_name:
            return lead.company_name
        return '[project name]'

    def _extract_technical_detail(self, lead: Lead) -> str:
        """Extract a specific technical detail."""
        return 'the architecture'

    def _extract_problem_space(self, lead: Lead) -> str:
        """Extract problem space being addressed."""
        return self._extract_topic(lead)

    def _extract_hackathon(self, lead: Lead) -> str:
        """Extract hackathon name."""
        return '[hackathon name]'

    def _extract_prize(self, lead: Lead) -> str:
        """Extract prize won."""
        return 'winning'

    def _extract_project_title(self, lead: Lead) -> str:
        """Extract project title."""
        return self._extract_paper_title(lead)

    def _extract_lab_name(self, lead: Lead) -> str:
        """Extract lab name."""
        return 'the lab'

    def _extract_accelerator(self, lead: Lead) -> str:
        """Extract accelerator name."""
        accelerators = ['Entrepreneur First', 'Techstars', 'Antler', 'Y Combinator']
        if lead.outreach_hook:
            for acc in accelerators:
                if acc.lower() in lead.outreach_hook.lower():
                    return acc
        return '[accelerator]'

    def _extract_area_from_source(self, lead: Lead, source: str) -> str:
        """Extract area description from source."""
        source_areas = {
            'arxiv': 'research',
            'github': 'engineering',
            'conference': 'academic community',
            'hackathon': 'hackathons',
            'twitter': 'public building',
        }
        return source_areas.get(source, source)

    def _format_signal(self, source: str) -> str:
        """Format source as a signal description."""
        signal_formats = {
            'arxiv': 'your recent paper on arXiv',
            'github': 'your GitHub project',
            'conference': 'your conference talk',
            'hackathon': 'your hackathon win',
            'eu_grants': 'your ERC grant',
            'twitter': 'your updates on Twitter',
        }
        return signal_formats.get(source, f'your {source} activity')

    def _generate_custom_hook(self, lead: Lead) -> str:
        """Generate a custom hook based on lead's readiness."""
        if lead.readiness == 'HOT':
            return ("Given the momentum in your work, now might be an interesting time to "
                    "explore what's possible on the commercial side.")
        elif lead.readiness == 'WARM':
            return ("If you're ever considering the commercial potential of your work, "
                    "I'd love to be a sounding board.")
        else:
            return ("I'd be curious to hear your thoughts on the commercial applications "
                    "of your research.")

    def _generate_generic_message(
        self,
        lead: Lead,
        sender_name: str,
        custom_hook: Optional[str]
    ) -> Dict[str, str]:
        """Generate generic message as fallback."""
        first_name = lead.name.split()[0] if lead.name else ''
        area = self._extract_topic(lead)

        subject = f"Your work in {area}"
        body = f"""Hi {first_name},

I came across your work in {area} and was impressed by your technical approach.

I'm {sender_name} from Ellipsis Venture. We back technical founders building AI companies in Europe at the earliest stages.

{custom_hook or self._generate_custom_hook(lead)}

Would you be open to a brief conversation about what you're working on?

Best,
{sender_name}"""

        return {
            'subject': subject,
            'body': body,
            'template_used': 'generic',
            'variables': {'first_name': first_name, 'area': area},
        }

    def generate_linkedin_message(self, lead: Lead, sender_name: str = "Your Name") -> str:
        """
        Generate shorter LinkedIn connection message (300 char limit).

        LinkedIn connection requests have strict character limits.
        """
        first_name = lead.name.split()[0] if lead.name else ''
        sources = self._get_lead_sources(lead)

        if 'arxiv' in sources:
            return (f"Hi {first_name}, I came across your recent paper and was impressed. "
                    f"I'm {sender_name} from Ellipsis Venture - we back AI founders in Europe. "
                    f"Would love to connect!")

        if 'conference' in sources:
            return (f"Hi {first_name}, saw your talk recently - great work! "
                    f"I'm {sender_name} from Ellipsis Venture. We invest in technical founders. "
                    f"Would love to connect!")

        # Multi-signal
        if len(sources) >= 2:
            return (f"Hi {first_name}, I've been following your work across {sources[0]} and {sources[1]}. "
                    f"I'm {sender_name} from Ellipsis Venture - we back AI founders. Connect?")

        # Generic
        return (f"Hi {first_name}, impressed by your work in AI. "
                f"I'm {sender_name} from Ellipsis Venture - we invest in technical founders. "
                f"Would love to connect!")
