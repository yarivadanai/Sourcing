"""University spin-off companies data source."""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from config.settings import settings
from pipeline.sources.base import BaseSource, RawLead


class UniversitySpinoffsSource(BaseSource):
    """Collect leads from university spin-off companies."""

    def __init__(self):
        super().__init__("spinoff")
        self.universities = self._get_university_config()

    def _get_university_config(self) -> Dict:
        """
        Comprehensive configuration for European universities.

        Covers: Switzerland, UK, Sweden, Germany, and other top European institutions.
        """
        return {
            # === SWITZERLAND ===
            'eth_zurich': {
                'name': 'ETH Zurich',
                'country': 'Switzerland',
                'tier': 1,
                'spinoff_url': 'https://entrepreneurship.ethz.ch/en/spinoffs.html',
                'tech_transfer_url': 'https://transfer.ethz.ch/en/spin-offs.html',
                'scoring_bonus': 10,
            },
            'epfl': {
                'name': 'EPFL',
                'country': 'Switzerland',
                'tier': 1,
                'spinoff_url': 'https://www.epfl.ch/innovation/domain/startups/',
                'scoring_bonus': 10,
            },
            'university_zurich': {
                'name': 'University of Zurich',
                'country': 'Switzerland',
                'tier': 2,
                'spinoff_url': 'https://www.innovation.uzh.ch/en/spinoffs.html',
                'scoring_bonus': 7,
            },
            'university_basel': {
                'name': 'University of Basel',
                'country': 'Switzerland',
                'tier': 2,
                'spinoff_url': 'https://www.unibas.ch/en/Research/Spin-offs.html',
                'scoring_bonus': 7,
            },

            # === UNITED KINGDOM ===
            'oxford': {
                'name': 'University of Oxford',
                'country': 'UK',
                'tier': 1,
                'spinoff_url': 'https://innovation.ox.ac.uk/our-portfolio/',
                'scoring_bonus': 10,
            },
            'cambridge': {
                'name': 'University of Cambridge',
                'country': 'UK',
                'tier': 1,
                'spinoff_url': 'https://www.enterprise.cam.ac.uk/support-for-spinouts/',
                'scoring_bonus': 10,
            },
            'imperial': {
                'name': 'Imperial College London',
                'country': 'UK',
                'tier': 1,
                'spinoff_url': 'https://www.imperial.ac.uk/enterprise/staff/business-partnerships/spin-out-companies/',
                'scoring_bonus': 10,
            },
            'ucl': {
                'name': 'University College London',
                'country': 'UK',
                'tier': 1,
                'spinoff_url': 'https://www.uclb.com/portfolio',
                'scoring_bonus': 10,
            },
            'edinburgh': {
                'name': 'University of Edinburgh',
                'country': 'UK',
                'tier': 2,
                'spinoff_url': 'https://www.ed.ac.uk/research/impact/spinouts',
                'scoring_bonus': 8,
            },
            'manchester': {
                'name': 'University of Manchester',
                'country': 'UK',
                'tier': 2,
                'spinoff_url': 'https://www.manchester.ac.uk/research/impact/spin-outs/',
                'scoring_bonus': 7,
            },
            'kings_college': {
                'name': "King's College London",
                'country': 'UK',
                'tier': 2,
                'spinoff_url': 'https://www.kcl.ac.uk/research/innovation-spinouts',
                'scoring_bonus': 7,
            },
            'bristol': {
                'name': 'University of Bristol',
                'country': 'UK',
                'tier': 2,
                'spinoff_url': 'https://www.bristol.ac.uk/research/impact/spinouts/',
                'scoring_bonus': 7,
            },

            # === SWEDEN ===
            'kth': {
                'name': 'KTH Royal Institute of Technology',
                'country': 'Sweden',
                'tier': 1,
                'spinoff_url': 'https://www.kth.se/en/innovation/startups',
                'scoring_bonus': 10,
            },
            'chalmers': {
                'name': 'Chalmers University of Technology',
                'country': 'Sweden',
                'tier': 2,
                'spinoff_url': 'https://www.chalmers.se/en/collaboration/innovation-entrepreneurship/',
                'scoring_bonus': 8,
            },
            'lund': {
                'name': 'Lund University',
                'country': 'Sweden',
                'tier': 2,
                'spinoff_url': 'https://www.lunduniversity.lu.se/research-and-innovation/innovation-and-entrepreneurship',
                'scoring_bonus': 7,
            },
            'karolinska': {
                'name': 'Karolinska Institute',
                'country': 'Sweden',
                'tier': 1,
                'spinoff_url': 'https://ki.se/en/innovation/spin-offs',
                'scoring_bonus': 9,
            },

            # === GERMANY ===
            'tum': {
                'name': 'Technical University of Munich',
                'country': 'Germany',
                'tier': 1,
                'spinoff_url': 'https://www.tum.de/en/innovation/entrepreneurship/start-ups',
                'scoring_bonus': 10,
            },
            'rwth_aachen': {
                'name': 'RWTH Aachen University',
                'country': 'Germany',
                'tier': 2,
                'spinoff_url': 'https://www.rwth-aachen.de/cms/root/Forschung/Wissens-Technologietransfer/~bksd/Spin-offs/',
                'scoring_bonus': 8,
            },
            'tu_berlin': {
                'name': 'TU Berlin',
                'country': 'Germany',
                'tier': 2,
                'spinoff_url': 'https://www.tu.berlin/en/transfer/entrepreneurship',
                'scoring_bonus': 7,
            },
            'heidelberg': {
                'name': 'Heidelberg University',
                'country': 'Germany',
                'tier': 2,
                'spinoff_url': 'https://www.uni-heidelberg.de/en/research/transfer-innovation',
                'scoring_bonus': 7,
            },
            'lmu_munich': {
                'name': 'LMU Munich',
                'country': 'Germany',
                'tier': 2,
                'spinoff_url': 'https://www.lmu.de/en/about-lmu/structure/central-university-administration/transfer-and-entrepreneurship/',
                'scoring_bonus': 7,
            },
            'karlsruhe': {
                'name': 'Karlsruhe Institute of Technology',
                'country': 'Germany',
                'tier': 2,
                'spinoff_url': 'https://www.kit.edu/english/innovation_spin-offs.php',
                'scoring_bonus': 8,
            },
            'max_planck': {
                'name': 'Max Planck Society',
                'country': 'Germany',
                'tier': 1,
                'spinoff_url': 'https://www.max-planck-innovation.de/en/spin-offs',
                'scoring_bonus': 9,
            },

            # === NETHERLANDS ===
            'tu_delft': {
                'name': 'TU Delft',
                'country': 'Netherlands',
                'tier': 1,
                'spinoff_url': 'https://www.tudelft.nl/en/innovation-impact/valorisation/startups',
                'scoring_bonus': 9,
            },
            'eindhoven': {
                'name': 'TU Eindhoven',
                'country': 'Netherlands',
                'tier': 2,
                'spinoff_url': 'https://www.tue.nl/en/our-university/entrepreneurship',
                'scoring_bonus': 8,
            },
            'amsterdam': {
                'name': 'University of Amsterdam',
                'country': 'Netherlands',
                'tier': 1,
                'spinoff_url': 'https://innovation.uva.nl/entrepreneurs/spin-offs',
                'scoring_bonus': 8,
            },
            'wageningen': {
                'name': 'Wageningen University',
                'country': 'Netherlands',
                'tier': 2,
                'spinoff_url': 'https://www.wur.nl/en/research-results/valorisation/spin-offs.htm',
                'scoring_bonus': 7,
            },

            # === FRANCE ===
            'sorbonne': {
                'name': 'Sorbonne University',
                'country': 'France',
                'tier': 2,
                'spinoff_url': 'https://www.sorbonne-universite.fr/en/innovation-and-entrepreneurship',
                'scoring_bonus': 7,
            },
            'ecole_polytechnique': {
                'name': 'École Polytechnique',
                'country': 'France',
                'tier': 1,
                'spinoff_url': 'https://www.polytechnique.edu/en/innovation-entrepreneurship',
                'scoring_bonus': 9,
            },
            'ens_paris': {
                'name': 'ENS Paris',
                'country': 'France',
                'tier': 1,
                'spinoff_url': 'https://www.ens.psl.eu/en/innovation',
                'scoring_bonus': 9,
            },
            'inria': {
                'name': 'INRIA',
                'country': 'France',
                'tier': 1,
                'spinoff_url': 'https://www.inria.fr/en/innovation-entrepreneurship',
                'scoring_bonus': 9,
            },

            # === BELGIUM ===
            'ku_leuven': {
                'name': 'KU Leuven',
                'country': 'Belgium',
                'tier': 2,
                'spinoff_url': 'https://www.kuleuven.be/english/research/rd/p_d/spin-offs',
                'scoring_bonus': 8,
            },

            # === DENMARK ===
            'dtu': {
                'name': 'Technical University of Denmark',
                'country': 'Denmark',
                'tier': 2,
                'spinoff_url': 'https://www.dtu.dk/english/about/collaboration/spin-outs',
                'scoring_bonus': 8,
            },

            # === NORWAY ===
            'ntnu': {
                'name': 'Norwegian University of Science and Technology',
                'country': 'Norway',
                'tier': 2,
                'spinoff_url': 'https://www.ntnu.edu/innovation/spin-offs',
                'scoring_bonus': 7,
            },

            # === AUSTRIA ===
            'tu_vienna': {
                'name': 'TU Wien',
                'country': 'Austria',
                'tier': 2,
                'spinoff_url': 'https://www.tuwien.at/en/research/forschungsfoerderung/spin-offs',
                'scoring_bonus': 7,
            },
        }

    def collect(self) -> List[RawLead]:
        """Collect spin-offs from all configured universities."""
        self.logger.info(f"Collecting university spin-offs from {len(self.universities)} universities")

        leads = []

        for uni_key, uni_config in self.universities.items():
            try:
                uni_leads = self._collect_university(uni_key, uni_config)
                leads.extend(uni_leads)
                self.logger.info(f"{uni_config['name']}: {len(uni_leads)} spin-offs")
            except Exception as e:
                self.logger.error(f"Failed to collect from {uni_config['name']}: {e}")

        self.log_result(len(leads))
        return leads

    def _collect_university(self, uni_key: str, uni_config: Dict) -> List[RawLead]:
        """
        Collect spin-offs from a specific university.

        Note: Each university has different website structure.
        This is a template - customize per university.
        """
        leads = []

        try:
            response = requests.get(uni_config['spinoff_url'], timeout=30)
            if response.status_code != 200:
                return leads

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for spin-off companies
            # NOTE: Selectors vary by university - customize as needed
            spinoff_items = soup.find_all('div', class_='spinoff-item')  # Placeholder selector

            for item in spinoff_items:
                try:
                    # Extract company name
                    name_elem = item.find('h3') or item.find('h2')
                    if not name_elem:
                        continue
                    company_name = name_elem.get_text().strip()

                    # Extract description
                    desc_elem = item.find('p', class_='description')
                    description = desc_elem.get_text().strip() if desc_elem else ''

                    # Filter for AI/Deep Tech
                    if not self._is_ai_related(description):
                        continue

                    # Extract founder names (if available)
                    founders_elem = item.find('div', class_='founders')
                    founders = []
                    if founders_elem:
                        founders_text = founders_elem.get_text()
                        founders = [f.strip() for f in founders_text.split(',')]

                    # Extract website
                    website_elem = item.find('a', class_='website')
                    website = website_elem['href'] if website_elem else None

                    # Extract founding year
                    year_elem = item.find('span', class_='year')
                    founded_year = year_elem.get_text().strip() if year_elem else None
                    months_old = self._calculate_months_old(founded_year)

                    # Filter for recent spin-offs (last 3 years)
                    if months_old > 36:
                        continue

                    # Create leads for each founder (or use company name if no founders listed)
                    if not founders:
                        founders = [f"Founder of {company_name}"]

                    for founder_name in founders:
                        lead = RawLead(
                            name=founder_name,
                            source='spinoff',
                            university_affiliation=uni_config['name'],
                            company_name=company_name,
                            company_website=website,
                            location=uni_config['country'],
                            source_url=uni_config['spinoff_url'],
                            raw_data={
                                'university_tier': uni_config['tier'],
                                'university_country': uni_config['country'],
                                'sector': description,
                                'founded_year': founded_year,
                                'months_old': months_old,
                                'company_description': description,
                            }
                        )

                        leads.append(lead)

                except Exception as e:
                    self.logger.warning(f"Failed to process spin-off: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scrape {uni_config['name']}: {e}")

        return leads

    def _is_ai_related(self, text: str) -> bool:
        """Check if description is AI/Deep Tech related."""
        if not text:
            return False

        ai_keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural', 'nlp', 'computer vision', 'robotics', 'autonomous',
            'llm', 'large language', 'generative', 'foundation model',
            'biotech', 'drug discovery', 'protein', 'quantum', 'photonics',
            'semiconductor', 'chip', 'hardware', 'quantum computing'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ai_keywords)

    def _calculate_months_old(self, founded_year: Optional[str]) -> int:
        """Calculate months since founding."""
        if not founded_year:
            return 999  # Unknown age

        try:
            year = int(founded_year)
            current_year = datetime.now().year
            return (current_year - year) * 12
        except ValueError:
            return 999
