"""
similarity_scorer.py — Layer 3b: Similarity Scorer Module
Computes semantic similarity between resume and job description using
Sentence-BERT (all-MiniLM-L6-v2) and cosine similarity.
Also derives matched and missing skill sets via set operations.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class ValidationError(ValueError):
    """Raised when scorer receives empty inputs."""
    pass


class SimilarityScorer:
    """
    Generates Sentence-BERT embeddings and computes cosine similarity
    normalised to a 0–100% compatibility score.
    """

    def __init__(self):
        # Model loaded once at startup; shared across all sessions
        self._model = SentenceTransformer("all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_score(self, resume_text: str, jd_text: str) -> float:
        """
        Compute semantic compatibility score between resume and JD.

        Args:
            resume_text: Preprocessed resume text.
            jd_text:     Preprocessed job-description text.

        Returns:
            float: Score in [0.0, 100.0] rounded to 2 decimal places.

        Raises:
            ValidationError: If either input is empty.
        """
        if not resume_text or not resume_text.strip():
            raise ValidationError("Resume text must not be empty.")
        if not jd_text or not jd_text.strip():
            raise ValidationError("Job description text must not be empty.")

        embeddings = self._model.encode(
            [resume_text, jd_text], convert_to_numpy=True
        )
        resume_vec = embeddings[0]
        jd_vec = embeddings[1]

        # Cosine similarity
        dot = float(np.dot(resume_vec, jd_vec))
        norm_product = float(np.linalg.norm(resume_vec) * np.linalg.norm(jd_vec))

        if norm_product == 0:
            return 0.0

        cosine_sim = dot / norm_product
        score = round(cosine_sim * 100, 2)
        return float(np.clip(score, 0.0, 100.0))

    def get_skill_sets(
        self, resume_skills: set[str], jd_skills: set[str]
    ) -> tuple[set[str], set[str]]:
        """
        Derive matched and missing skill sets via set operations.

        Args:
            resume_skills: Skills extracted from the resume.
            jd_skills:     Skills extracted from the job description.

        Returns:
            tuple[set[str], set[str]]: (matched_skills, missing_skills)
        """
        matched = resume_skills & jd_skills          # intersection
        missing = jd_skills - resume_skills          # difference
        return matched, missing
