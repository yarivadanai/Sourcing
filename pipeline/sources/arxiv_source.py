"""ArXiv academic papers data source."""

import arxiv
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class ArxivSource(BaseSource):
    """Collect leads from ArXiv academic papers."""

    def __init__(self):
        super().__init__("arxiv")
        self.client = arxiv.Client()

    def collect(self) -> List[RawLead]:
        """Collect papers from ArXiv in target categories."""
        self.logger.info(f"Collecting ArXiv papers from last {settings.days_back_arxiv} days")

        leads = []

        for category in settings.arxiv_categories:
            try:
                papers = self._fetch_papers_by_category(category, settings.days_back_arxiv)
                self.logger.info(f"Category {category}: {len(papers)} papers")

                for paper in papers:
                    paper_leads = self._process_paper(paper)
                    leads.extend(paper_leads)

            except Exception as e:
                self.logger.error(f"Failed to fetch papers for category {category}: {e}")

        self.log_result(len(leads))
        return leads

    def _fetch_papers_by_category(self, category: str, days_back: int) -> List:
        """Fetch papers from a specific category."""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        search = arxiv.Search(
            query=f"cat:{category}",
            max_results=500,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        papers = []
        for paper in self.client.results(search):
            if paper.published.replace(tzinfo=None) >= start_date:
                papers.append(paper)
            else:
                break  # Papers are sorted by date, so we can stop

        return papers

    def _process_paper(self, paper) -> List[RawLead]:
        """Process a paper and extract leads from authors."""
        leads = []

        # Extract ArXiv ID
        arxiv_id = paper.entry_id.split('/')[-1]

        # Get categories
        categories = paper.categories

        # Calculate days old
        days_old = (datetime.now() - paper.published.replace(tzinfo=None)).days

        # Process each author
        for idx, author in enumerate(paper.authors):
            author_name = author.name

            # Note: ArXiv API often doesn't include affiliations
            # We'll try to get it, but it may be None
            affiliation = None
            if hasattr(author, 'affiliation') and author.affiliation:
                affiliation = author.affiliation

            # Filter for European affiliations (if we have them)
            # If no affiliation data, we'll include all authors and filter later during enrichment
            if affiliation:
                if not self.is_european_affiliation(
                    affiliation,
                    settings.tier_1_universities,
                    settings.tier_2_universities
                ):
                    continue  # Skip non-European authors

            # Create lead
            lead = RawLead(
                name=author_name,
                source='arxiv',
                university_affiliation=affiliation,
                source_url=f"https://arxiv.org/abs/{arxiv_id}",
                raw_data={
                    'arxiv_id': arxiv_id,
                    'paper_title': paper.title,
                    'paper_topic': ', '.join(categories),
                    'topics': categories,
                    'is_first_author': (idx == 0),
                    'author_position': idx,
                    'days_old': days_old,
                    'abstract': paper.summary[:500],  # First 500 chars
                    'published_date': paper.published.isoformat(),
                    'pdf_url': paper.pdf_url,
                    # Citation count would need Semantic Scholar API
                    'citation_count': 0,
                }
            )

            leads.append(lead)

        return leads

    def enrich_with_semantic_scholar(self, arxiv_id: str) -> Optional[dict]:
        """
        Enrich paper data with Semantic Scholar API.

        This provides:
        - Author affiliations (more complete than ArXiv)
        - Citation counts
        - Author h-index
        - Influential citation count
        """
        try:
            from semanticscholar import SemanticScholar

            sch = SemanticScholar()

            # Search by ArXiv ID
            paper = sch.get_paper(f"ARXIV:{arxiv_id}")

            if paper:
                authors_data = []
                for author in paper.authors:
                    author_info = {
                        'name': author.name,
                        'authorId': author.authorId,
                        'affiliations': getattr(author, 'affiliations', []),
                    }

                    # Get additional author details if available
                    if hasattr(author, 'hIndex'):
                        author_info['h_index'] = author.hIndex

                    authors_data.append(author_info)

                return {
                    'authors': authors_data,
                    'citation_count': paper.citationCount,
                    'influential_citation_count': getattr(paper, 'influentialCitationCount', 0),
                    'year': paper.year,
                }

        except Exception as e:
            self.logger.warning(f"Failed to enrich with Semantic Scholar for {arxiv_id}: {e}")

        return None
