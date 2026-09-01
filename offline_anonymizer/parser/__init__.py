"""Document parsers."""

from offline_anonymizer.parser.docx_parser import DocxParser
from offline_anonymizer.parser.factory import ParserFactory
from offline_anonymizer.parser.markdown_parser import MarkdownParser
from offline_anonymizer.parser.txt_parser import TxtParser

__all__ = ["DocxParser", "MarkdownParser", "ParserFactory", "TxtParser"]
