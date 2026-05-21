"""
skill_extractor.py — Layer 3b: Skill Extractor Module
Dual-pronged skill extraction using spaCy NER and KeyBERT keyword mining.
"""

from __future__ import annotations

import spacy
from keybert import KeyBERT


class SkillExtractor:
    """
    Extracts skills and relevant keywords from document text by combining:
      - spaCy Named Entity Recognition (ORG, PRODUCT, GPE entities)
      - KeyBERT contextual keyphrase extraction
    """

    # Minimum KeyBERT relevance score to include a keyword
    _KW_THRESHOLD = 0.30
    # Number of top keyphrases KeyBERT should return per document
    _TOP_N = 20

    def __init__(self):
        self._nlp = spacy.load("en_core_web_sm")
        # KeyBERT reuses the same SBERT model family for consistency
        self._kw_model = KeyBERT(model="all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_skills(self, text: str) -> set[str]:
        """
        Return a deduplicated set of lowercase skills/keywords for one document.

        Args:
            text: Preprocessed (or raw) document text.

        Returns:
            set[str]: Union of NER entities and KeyBERT keyphrases.
        """
        if not text or not text.strip():
            return set()

        ner_skills = self._extract_ner(text)
        kw_skills = self._extract_keywords(text)
        return ner_skills | kw_skills

    def extract_both(
        self, resume_text: str, jd_text: str
    ) -> tuple[set[str], set[str]]:
        """
        Convenience method: extract skills from both documents in one call.

        Returns:
            tuple[set[str], set[str]]: (resume_skills, jd_skills)
        """
        resume_skills = self.extract_skills(resume_text)
        jd_skills = self.extract_skills(jd_text)
        return resume_skills, jd_skills

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_ner(self, text: str) -> set[str]:
        """Run spaCy NER and collect relevant entity labels."""
        doc = self._nlp(text)
        target_labels = {"ORG", "PRODUCT", "GPE", "WORK_OF_ART", "LAW"}
        return {
            ent.text.lower().strip()
            for ent in doc.ents
            if ent.label_ in target_labels and len(ent.text.strip()) > 1
        }

    def _extract_keywords(self, text: str) -> set[str]:
        """Run KeyBERT keyphrase extraction with bi-gram support."""
        kw_pairs = self._kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=self._TOP_N,
            use_mmr=True,
            diversity=0.5,
        )
        return {
            kw.lower().strip()
            for kw, score in kw_pairs
            if score >= self._KW_THRESHOLD and len(kw.strip()) > 1
        }
