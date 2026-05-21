"""
pdf_parser.py — Layer 3a: PDF Parser Module
Extracts plain text from uploaded PDF resume files using pdfplumber.
"""

import pdfplumber


class PDFParseError(Exception):
    """Raised when a PDF cannot be parsed or yields no extractable text."""
    pass


class PDFParser:
    """
    Responsible for accepting a PDF file object and returning its full
    text content as a plain string.
    """

    MAX_PAGES = 10  # SRS cap: 5-page resume; allow extra margin

    def extract(self, file_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            str: Concatenated text from all pages.

        Raises:
            PDFParseError: If the file cannot be opened or yields no text.
        """
        if file_path is None:
            raise PDFParseError("No file provided.")

        try:
            with pdfplumber.open(file_path) as pdf:
                pages = pdf.pages[: self.MAX_PAGES]
                extracted = []
                for page in pages:
                    text = page.extract_text()
                    if text:
                        extracted.append(text.strip())

            if not extracted:
                raise PDFParseError(
                    "Could not extract text from the PDF. "
                    "It may be a scanned image. Please paste your resume text instead."
                )

            return "\n".join(extracted)

        except PDFParseError:
            raise
        except Exception as exc:
            raise PDFParseError(
                f"Failed to open or read PDF: {exc}. "
                "Please paste your resume text instead."
            ) from exc
