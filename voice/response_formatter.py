"""ResponseFormatter: Formats responses for natural voice delivery.

Converts text responses to voice-friendly format, removes markdown,
handles citations, generates SSML for prosody/emphasis,
and chunks long responses.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseDomain(Enum):
    """Response domain types."""
    LEGAL = "legal"
    FINANCIAL = "financial"
    PROCEDURAL = "procedural"
    GENERAL = "general"


@dataclass
class FormattingConfig:
    """Configuration for response formatting."""
    remove_markdown: bool = True
    convert_tables_to_speech: bool = True
    chunk_long_responses: bool = True
    max_chunk_length: int = 500  # words
    add_emphasis: bool = True
    add_pauses: bool = True
    use_ssml: bool = True
    spell_out_acronyms: bool = True
    expand_numbers: bool = True
    use_proper_citations: bool = True


@dataclass
class ActionItem:
    """Extracted action item from response."""
    description: str
    priority: str = "normal"  # low, normal, high
    deadline: Optional[str] = None
    responsible_party: Optional[str] = None


class CitationFormatter:
    """Formats legal citations for voice reading."""

    @staticmethod
    def format_case_citation(citation: str) -> str:
        """Convert case citation to spoken form.
        
        Example: "Smith v. Jones, 123 F.3d 456 (9th Cir. 2019)"
        Becomes: "Smith versus Jones, reported at one twenty-three F third, 
                  four five six, Ninth Circuit, two thousand nineteen"
        
        Args:
            citation: Case citation text
            
        Returns:
            Spoken form of citation
        """
        # Replace "v." with "versus"
        spoken = citation.replace(" v. ", " versus ")
        
        # Pattern: Extract reporter volume, reporter, page
        match = re.search(r"(\d+)\s+([A-Z\.]+)\s+(\d+)", spoken)
        if match:
            volume = match.group(1)
            reporter = match.group(2).replace(".", " ")
            page = match.group(3)
            
            # Spell out volume and page
            volume_spoken = CitationFormatter._number_to_words(volume)
            page_spoken = CitationFormatter._spell_out_number(page)
            
            spoken = re.sub(
                r"\d+\s+[A-Z\.]+\s+\d+",
                f"{volume_spoken} {reporter} {page_spoken}",
                spoken
            )
        
        # Handle year in parentheses
        year_match = re.search(r"\((\d{4})\)", spoken)
        if year_match:
            year = year_match.group(1)
            year_spoken = CitationFormatter._number_to_words(year)
            spoken = spoken.replace(f"({year})", year_spoken)
        
        return spoken

    @staticmethod
    def format_statute_citation(statute: str) -> str:
        """Convert statute citation to spoken form.
        
        Example: "42 U.S.C. § 1983"
        Becomes: "Forty-two United States Code Section nineteen eighty-three"
        
        Args:
            statute: Statute citation
            
        Returns:
            Spoken form
        """
        spoken = statute
        
        # Replace common abbreviations
        spoken = spoken.replace("U.S.C.", "United States Code")
        spoken = spoken.replace("U.S.A.", "United States of America")
        spoken = spoken.replace("§", "Section")
        spoken = spoken.replace("Sec.", "Section")
        
        # Number conversions
        numbers = re.findall(r"\d+", spoken)
        for num in numbers:
            if num.startswith("0"):
                # Keep leading zeros like "01"
                spoken = spoken.replace(num, CitationFormatter._spell_out_number(num))
            else:
                # Regular number conversion
                spoken = spoken.replace(num, CitationFormatter._number_to_words(num), 1)
        
        return spoken

    @staticmethod
    def _number_to_words(num_str: str) -> str:
        """Convert number to words (e.g., '42' -> 'forty-two')."""
        try:
            num = int(num_str)
        except ValueError:
            return num_str

        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                "sixteen", "seventeen", "eighteen", "nineteen"]

        if num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + ("-" + ones[num % 10] if num % 10 != 0 else "")
        elif num < 1000:
            return ones[num // 100] + " hundred" + (
                " " + CitationFormatter._number_to_words(str(num % 100)) if num % 100 != 0 else ""
            )
        elif num < 1000000:
            return CitationFormatter._number_to_words(str(num // 1000)) + " thousand" + (
                " " + CitationFormatter._number_to_words(str(num % 1000)) if num % 1000 != 0 else ""
            )
        elif num < 1000000000:
            return CitationFormatter._number_to_words(str(num // 1000000)) + " million" + (
                " " + CitationFormatter._number_to_words(str(num % 1000000)) if num % 1000000 != 0 else ""
            )
        else:
            return num_str

    @staticmethod
    def _spell_out_number(num_str: str) -> str:
        """Spell out number digit by digit (e.g., '123' -> 'one two three')."""
        ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        return " ".join([ones[int(d)] for d in num_str])


class FinancialFormatter:
    """Formats financial information for voice delivery."""

    @staticmethod
    def format_currency(amount_str: str) -> str:
        """Format currency for speech.
        
        Example: "$1,234,567.89" -> "one million, two hundred thirty-four thousand,
                                     five hundred sixty-seven dollars and eighty-nine cents"
        
        Args:
            amount_str: Currency string
            
        Returns:
            Spoken form
        """
        # Extract just the number
        match = re.search(r"[\d,]+\.?\d*", amount_str)
        if not match:
            return amount_str

        num_str = match.group().replace(",", "")
        
        try:
            amount = float(num_str)
        except ValueError:
            return amount_str

        # Convert dollars
        dollars = int(amount)
        cents = round((amount - dollars) * 100)

        dollar_words = CitationFormatter._number_to_words(str(dollars))
        result = f"{dollar_words} dollars"

        if cents > 0:
            cent_words = CitationFormatter._number_to_words(str(cents))
            result += f" and {cent_words} cents"

        return result

    @staticmethod
    def format_percentage(percent_str: str) -> str:
        """Format percentage for speech.
        
        Args:
            percent_str: Percentage string
            
        Returns:
            Spoken form
        """
        match = re.search(r"(\d+\.?\d*)\s*%", percent_str)
        if match:
            num = match.group(1)
            return f"{CitationFormatter._number_to_words(num.split('.')[0])} percent"
        return percent_str


class ResponseFormatter:
    """Main formatter for voice-friendly responses."""

    def __init__(self, config: Optional[FormattingConfig] = None):
        """Initialize formatter.
        
        Args:
            config: FormattingConfig instance
        """
        self.config = config or FormattingConfig()
        self.citation_formatter = CitationFormatter()
        self.financial_formatter = FinancialFormatter()

    def format_for_speech(self, response: str, domain: ResponseDomain) -> str:
        """Format response for voice delivery.
        
        Args:
            response: Original response text
            domain: Response domain (legal, financial, etc.)
            
        Returns:
            Voice-friendly formatted response
        """
        text = response

        # Remove markdown formatting
        if self.config.remove_markdown:
            text = self._remove_markdown(text)

        # Convert tables
        if self.config.convert_tables_to_speech:
            text = self._convert_tables(text)

        # Format citations based on domain
        if domain == ResponseDomain.LEGAL:
            text = self._format_legal_content(text)
        elif domain == ResponseDomain.FINANCIAL:
            text = self._format_financial_content(text)

        # Expand acronyms
        if self.config.spell_out_acronyms:
            text = self._expand_acronyms(text)

        # Normalize spacing
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def generate_ssml(self, text: str, domain: ResponseDomain = ResponseDomain.GENERAL) -> str:
        """Generate SSML markup for prosody and emphasis.
        
        Args:
            text: Input text
            domain: Response domain
            
        Returns:
            SSML-formatted text
        """
        if not self.config.use_ssml:
            return text

        ssml = '<speak>'

        # Add emphasis to key terms
        if self.config.add_emphasis:
            ssml += self._add_emphasis(text, domain)
        else:
            ssml += text

        # Add pauses at sentence boundaries
        if self.config.add_pauses:
            ssml = re.sub(r'(\. )', r'</s><s>', ssml)
            ssml = re.sub(r'(\? )', r'</s><s>', ssml)
            ssml = re.sub(r'(! )', r'</s><s>', ssml)

        ssml += '</speak>'
        return ssml

    def summarize_for_speech(self, long_response: str, max_length: int = 150) -> str:
        """Create concise summary of long response.
        
        Args:
            long_response: Original long response
            max_length: Maximum words in summary
            
        Returns:
            Summarized response
        """
        sentences = re.split(r'[.!?]+', long_response)
        sentences = [s.strip() for s in sentences if s.strip()]

        summary_sentences = []
        word_count = 0
        target_words = max_length

        for sentence in sentences:
            words = sentence.split()
            word_count += len(words)
            summary_sentences.append(sentence)

            if word_count >= target_words:
                break

        summary = '. '.join(summary_sentences)
        if not summary.endswith(('.', '!', '?')):
            summary += '.'

        return summary

    def extract_action_items(self, response: str) -> List[ActionItem]:
        """Extract action items from response.
        
        Args:
            response: Response text
            
        Returns:
            List of action items
        """
        action_items = []

        # Patterns for action items
        patterns = [
            r"you (?:should|must|need to)\s+([^.!?]+)",
            r"please\s+([^.!?]+)",
            r"recommend(?:ed)?\s+(?:that\s+)?(?:you\s+)?([^.!?]+)",
            r"action.*?:\s*([^.!?]+)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                action_items.append(ActionItem(
                    description=match.group(1).strip(),
                    priority="high" if "immediately" in response else "normal"
                ))

        return action_items

    def chunk_response(self, response: str) -> List[str]:
        """Split long response into voice-friendly chunks.
        
        Args:
            response: Long response text
            
        Returns:
            List of response chunks
        """
        if not self.config.chunk_long_responses:
            return [response]

        sentences = re.split(r'(?<=[.!?])\s+', response)
        chunks = []
        current_chunk = []
        current_words = 0

        for sentence in sentences:
            words = sentence.split()
            word_count = len(words)

            if current_words + word_count > self.config.max_chunk_length and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_words = word_count
            else:
                current_chunk.append(sentence)
                current_words += word_count

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _remove_markdown(self, text: str) -> str:
        """Remove markdown formatting."""
        # Remove bold
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        
        # Remove italic
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Remove links but keep text
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Remove headings
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove blockquotes
        text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)

        return text

    def _convert_tables(self, text: str) -> str:
        """Convert markdown tables to prose."""
        # Simple table detection and conversion
        table_pattern = r'\|.*?\|.*?\n\|[\s\-|]+\n(?:\|.*?\|.*?\n)+'
        
        def table_to_prose(match):
            table_text = match.group(0)
            rows = [row.strip('| ').split('|') for row in table_text.split('\n') if row.strip()]
            
            prose = "Here is the information: "
            for row in rows[2:]:  # Skip header and separator
                prose += ', '.join([cell.strip() for cell in row if cell.strip()]) + '. '
            
            return prose

        text = re.sub(table_pattern, table_to_prose, text)
        return text

    def _format_legal_content(self, text: str) -> str:
        """Format legal citations and references."""
        # Format case citations
        case_pattern = r'\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+(?:,\s*\d+\s+[A-Z\.]+\s+\d+)?'
        text = re.sub(case_pattern, lambda m: self.citation_formatter.format_case_citation(m.group(0)), text)

        # Format statute references
        statute_pattern = r'(?:Section|§)\s+[\d\w\.\-]+'
        text = re.sub(statute_pattern, lambda m: self.citation_formatter.format_statute_citation(m.group(0)), text)

        return text

    def _format_financial_content(self, text: str) -> str:
        """Format financial amounts and percentages."""
        # Format currency
        currency_pattern = r'\$[\d,]+(?:\.\d{2})?'
        text = re.sub(currency_pattern, lambda m: self.financial_formatter.format_currency(m.group(0)), text)

        # Format percentages
        percent_pattern = r'\d+\.?\d*\s*%'
        text = re.sub(percent_pattern, lambda m: self.financial_formatter.format_percentage(m.group(0)), text)

        return text

    def _expand_acronyms(self, text: str) -> str:
        """Expand common acronyms."""
        acronyms = {
            r'\bLLC\b': 'Limited Liability Company',
            r'\bCorp\b': 'Corporation',
            r'\bInc\b': 'Incorporated',
            r'\bLtd\b': 'Limited',
            r'\bLLP\b': 'Limited Liability Partnership',
            r'\bSTT\b': 'Speech to Text',
            r'\bTTS\b': 'Text to Speech',
        }

        for pattern, expansion in acronyms.items():
            text = re.sub(pattern, expansion, text)

        return text

    def _add_emphasis(self, text: str, domain: ResponseDomain) -> str:
        """Add SSML emphasis tags to key terms."""
        if domain == ResponseDomain.LEGAL:
            key_terms = [
                r'(?:not?|must|shall|may|prohibited)',
                r'(?:important|critical|essential)',
            ]
        elif domain == ResponseDomain.FINANCIAL:
            key_terms = [
                r'(?:liability|risk|loss)',
                r'(?:profit|gain|return)',
            ]
        else:
            key_terms = []

        formatted = text
        for pattern in key_terms:
            formatted = re.sub(
                f'({pattern})',
                r'<emphasis level="strong">\1</emphasis>',
                formatted,
                flags=re.IGNORECASE
            )

        return formatted


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
