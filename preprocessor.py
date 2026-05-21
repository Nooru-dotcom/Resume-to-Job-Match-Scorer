"""
preprocessor.py — Layer 3b: Text Preprocessor Module
Cleans and normalises raw text using spaCy's linguistic pipeline.
Outputs a cleaned string suitable for embedding and skill extraction.
"""

import re
import spacy


class Preprocessor:
    """
    Lowercases text, strips punctuation and stopwords, and tokenises
    using spaCy's en_core_web_sm pipeline.
    """

    def __init__(self):
        self._nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])

    def clean(self, text: str) -> str:
        """
        Normalise raw document text.

        Steps:
            1. Strip excessive whitespace and control characters.
            2. Lowercase.
            3. Remove punctuation-only tokens and stopwords.
            4. Return the cleaned tokens joined as a single string.

        Args:
            text: Raw input string (resume or job description).

        Returns:
            str: Cleaned, normalised text.
        """
        if not text or not text.strip():
            return ""

        # Remove control chars and collapse whitespace
        text = re.sub(r"[\r\t\x0c\x0b]+", " ", text)
        text = re.sub(r" {2,}", " ", text).strip()

        doc = self._nlp(text.lower())

        tokens = [
            token.lemma_
            for token in doc
            if not token.is_stop
            and not token.is_punct
            and not token.is_space
            and len(token.text) > 1
        ]

        return " ".join(tokens)
