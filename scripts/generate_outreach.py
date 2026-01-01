"""
CLI tool for generating personalized outreach messages.

Usage:
    python scripts/generate_outreach.py --lead-id 123
    python scripts/generate_outreach.py --lead-name "John Doe"
    python scripts/generate_outreach.py --email john@example.com
    python scripts/generate_outreach.py --batch hot_leads.csv
"""

import sys
import csv
from pathlib import Path
from loguru import logger
from typing import Optional, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from pipeline.database import init_db, get_db
from pipeline.models import Lead
from pipeline.outreach.message_generator import OutreachMessageGenerator


logger.remove()
logger.add(sys.stderr, level="INFO")


class OutreachCLI:
    """CLI for generating outreach messages."""

    def __init__(self):
        self.generator = OutreachMessageGenerator()

    def find_lead(
        self,
        lead_id: Optional[int] = None,
        lead_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[Lead]:
        """Find lead by ID, name, or email."""
        with get_db() as db:
            if lead_id:
                return db.query(Lead).filter(Lead.id == lead_id).first()

            if email:
                return db.query(Lead).filter(Lead.email == email).first()

            if lead_name:
                # Fuzzy match on name
                leads = db.query(Lead).filter(
                    Lead.name.ilike(f"%{lead_name}%")
                ).all()

                if len(leads) == 1:
                    return leads[0]
                elif len(leads) > 1:
                    logger.warning(f"Multiple leads found matching '{lead_name}':")
                    for i, lead in enumerate(leads, 1):
                        logger.info(f"  {i}. {lead.name} ({lead.email or 'no email'})")
                    logger.info("\nPlease use --lead-id or --email for exact match")
                    return None
                else:
                    logger.error(f"No leads found matching '{lead_name}'")
                    return None

        return None

    def generate_for_lead(
        self,
        lead: Lead,
        sender_name: str = "Your Name",
        custom_hook: Optional[str] = None,
        template: Optional[str] = None,
        linkedin: bool = False,
        copy_to_clipboard: bool = False
    ):
        """Generate outreach message for a lead."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Generating outreach message for: {lead.name}")
        logger.info(f"{'='*60}\n")

        # Show lead context
        logger.info("📋 Lead Context:")
        logger.info(f"  Score: {lead.total_score:.1f}")
        logger.info(f"  Readiness: {lead.readiness}")
        if lead.university_affiliation:
            logger.info(f"  University: {lead.university_affiliation}")
        if lead.company_name:
            logger.info(f"  Company: {lead.company_name}")
        if lead.email:
            logger.info(f"  Email: {lead.email}")
        if lead.linkedin_url:
            logger.info(f"  LinkedIn: {lead.linkedin_url}")

        # Generate message
        if linkedin:
            message = self.generator.generate_linkedin_message(lead, sender_name)
            logger.info(f"\n📱 LinkedIn Connection Message:\n")
            logger.info(f"{message}")
            logger.info(f"\nCharacters: {len(message)}/300")

        else:
            result = self.generator.generate_message(
                lead,
                sender_name=sender_name,
                custom_hook=custom_hook,
                template_override=template
            )

            logger.info(f"\n📧 Email Outreach Message:")
            logger.info(f"\nTemplate Used: {result['template_used']}\n")
            logger.info(f"Subject: {result['subject']}\n")
            logger.info(result['body'])
            logger.info(f"\n{'='*60}")

            # Copy to clipboard if requested
            if copy_to_clipboard:
                try:
                    import pyperclip
                    full_message = f"Subject: {result['subject']}\n\n{result['body']}"
                    pyperclip.copy(full_message)
                    logger.success("\n✓ Message copied to clipboard!")
                except ImportError:
                    logger.warning("\n⚠ pyperclip not installed. Install with: pip install pyperclip")

    def generate_batch(
        self,
        csv_path: str,
        sender_name: str = "Your Name",
        output_path: Optional[str] = None
    ):
        """Generate outreach messages for all leads in a CSV."""
        logger.info(f"Generating outreach messages for leads in {csv_path}")

        leads = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try to find lead by email or name
                lead = self.find_lead(email=row.get('email'), lead_name=row.get('name'))
                if lead:
                    leads.append(lead)

        logger.info(f"Found {len(leads)} leads in database\n")

        # Generate messages
        messages = []
        for i, lead in enumerate(leads, 1):
            logger.info(f"[{i}/{len(leads)}] Generating for {lead.name}...")

            result = self.generator.generate_message(lead, sender_name=sender_name)
            messages.append({
                'name': lead.name,
                'email': lead.email or '',
                'linkedin_url': lead.linkedin_url or '',
                'subject': result['subject'],
                'body': result['body'],
                'template': result['template_used'],
                'score': lead.total_score,
                'readiness': lead.readiness,
            })

        # Save to CSV
        if output_path is None:
            output_path = csv_path.replace('.csv', '_with_messages.csv')

        with open(output_path, 'w', newline='') as f:
            fieldnames = ['name', 'email', 'linkedin_url', 'score', 'readiness',
                         'subject', 'body', 'template']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(messages)

        logger.success(f"\n✓ Saved {len(messages)} outreach messages to {output_path}")

    def list_templates(self):
        """List available templates."""
        logger.info("\n📝 Available Templates:\n")
        for name in self.generator.templates.keys():
            logger.info(f"  - {name}")
        logger.info("\nUse --template <name> to use a specific template")

    def show_template(self, template_name: str):
        """Show a specific template."""
        if template_name in self.generator.templates:
            logger.info(f"\n📝 Template: {template_name}\n")
            logger.info(self.generator.templates[template_name])
        else:
            logger.error(f"Template '{template_name}' not found")
            self.list_templates()


def main():
    """Main CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate personalized outreach messages for leads"
    )

    # Lead selection
    lead_group = parser.add_mutually_exclusive_group(required=False)
    lead_group.add_argument('--lead-id', type=int, help='Lead ID')
    lead_group.add_argument('--lead-name', type=str, help='Lead name (fuzzy match)')
    lead_group.add_argument('--email', type=str, help='Lead email')
    lead_group.add_argument('--batch', type=str, help='Path to CSV with leads')

    # Message options
    parser.add_argument('--sender-name', default='Your Name',
                       help='Your name (default: Your Name)')
    parser.add_argument('--custom-hook', type=str,
                       help='Custom hook to add to message')
    parser.add_argument('--template', type=str,
                       help='Template to use (see --list-templates)')
    parser.add_argument('--linkedin', action='store_true',
                       help='Generate LinkedIn message instead of email')
    parser.add_argument('--copy', action='store_true',
                       help='Copy message to clipboard (requires pyperclip)')

    # Batch options
    parser.add_argument('--output', type=str,
                       help='Output path for batch generation')

    # Utility
    parser.add_argument('--list-templates', action='store_true',
                       help='List available templates')
    parser.add_argument('--show-template', type=str,
                       help='Show a specific template')

    args = parser.parse_args()

    # Initialize database
    init_db()

    cli = OutreachCLI()

    # Handle utility commands
    if args.list_templates:
        cli.list_templates()
        return 0

    if args.show_template:
        cli.show_template(args.show_template)
        return 0

    # Batch generation
    if args.batch:
        cli.generate_batch(args.batch, args.sender_name, args.output)
        return 0

    # Single lead generation
    if not (args.lead_id or args.lead_name or args.email):
        parser.print_help()
        return 1

    lead = cli.find_lead(args.lead_id, args.lead_name, args.email)
    if not lead:
        return 1

    cli.generate_for_lead(
        lead,
        sender_name=args.sender_name,
        custom_hook=args.custom_hook,
        template=args.template,
        linkedin=args.linkedin,
        copy_to_clipboard=args.copy
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
