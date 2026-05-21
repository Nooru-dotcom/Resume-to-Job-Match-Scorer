"""
orchestrator.py — Layer 2: Application Logic (v2.0)
Enhanced with section-level resume parsing, readability scoring,
and richer analysis result dictionary.
"""
from __future__ import annotations
import re
from pdf_parser import PDFParser, PDFParseError
from preprocessor import Preprocessor
from skill_extractor import SkillExtractor
from similarity_scorer import SimilarityScorer, ValidationError
from suggestion_engine import SuggestionEngine


class Orchestrator:
    def __init__(self):
        self._pdf_parser = PDFParser()
        self._preprocessor = Preprocessor()
        self._skill_extractor = SkillExtractor()
        self._similarity_scorer = SimilarityScorer()
        self._suggestion_engine = SuggestionEngine(use_llm_fallback=True)

    def analyze(self, resume_input, jd_text: str) -> dict:
        valid, err_msg = self._validate_inputs(resume_input, jd_text)
        if not valid:
            return self._error_result(err_msg)

        try:
            if self._is_pdf(resume_input):
                resume_text = self._pdf_parser.extract(resume_input)
            else:
                resume_text = str(resume_input).strip()
        except PDFParseError as exc:
            return self._error_result(str(exc))

        if not resume_text:
            return self._error_result("Resume is empty. Please paste your text.")

        clean_resume = self._preprocessor.clean(resume_text)
        clean_jd = self._preprocessor.clean(jd_text)

        resume_skills, jd_skills = self._skill_extractor.extract_both(clean_resume, clean_jd)

        try:
            score = self._similarity_scorer.compute_score(clean_resume, clean_jd)
        except ValidationError as exc:
            return self._error_result(str(exc))

        matched, missing = self._similarity_scorer.get_skill_sets(resume_skills, jd_skills)
        suggestions = self._suggestion_engine.generate(missing, score)

        # Extra metrics
        word_count = len(resume_text.split())
        sentence_count = max(1, len(re.findall(r'[.!?]+', resume_text)))
        avg_sentence_len = round(word_count / sentence_count, 1)
        has_quantification = bool(re.search(r'\d+%|\d+ years?|\$\d+|\d+x\b', resume_text, re.I))
        sections_found = self._detect_sections(resume_text)

        return {
            "match_score": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "suggestions": suggestions,
            "error": None,
            # Extra
            "word_count": word_count,
            "avg_sentence_length": avg_sentence_len,
            "has_quantification": has_quantification,
            "sections_found": sections_found,
            "resume_skill_count": len(resume_skills),
            "jd_skill_count": len(jd_skills),
        }

    def _detect_sections(self, text: str) -> list[str]:
        known = ["experience", "education", "skills", "projects",
                 "certifications", "summary", "objective", "publications", "awards"]
        found = []
        lower = text.lower()
        for s in known:
            if s in lower:
                found.append(s.title())
        return found

    def _validate_inputs(self, resume_input, jd_text):
        has_resume = resume_input is not None and str(resume_input).strip() != ""
        has_jd = jd_text is not None and jd_text.strip() != ""
        if not has_resume and not has_jd:
            return False, "Both resume and job description are required."
        if not has_resume:
            return False, "Please upload a PDF or paste your resume text."
        if not has_jd:
            return False, "Please enter a job description."
        return True, ""

    @staticmethod
    def _is_pdf(resume_input) -> bool:
        if resume_input is None:
            return False
        s = str(resume_input)
        return s.lower().endswith(".pdf") and not s.strip().startswith(" ")

    @staticmethod
    def _error_result(message: str) -> dict:
        return {
            "match_score": None,
            "matched_skills": set(),
            "missing_skills": set(),
            "suggestions": [],
            "error": message,
            "word_count": 0,
            "avg_sentence_length": 0,
            "has_quantification": False,
            "sections_found": [],
            "resume_skill_count": 0,
            "jd_skill_count": 0,
        }
