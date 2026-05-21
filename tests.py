"""
tests.py — Unit & Integration Test Suite
Covers: Preprocessor, SkillExtractor, SimilarityScorer,
        SuggestionEngine, PDFParser, and Orchestrator.

Run with:
    python tests.py
Or via pytest:
    pytest tests.py -v
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Preprocessor Tests
# ---------------------------------------------------------------------------

class TestPreprocessor(unittest.TestCase):
    def setUp(self):
        from preprocessor import Preprocessor
        self.pp = Preprocessor()

    def test_empty_string_returns_empty(self):
        self.assertEqual(self.pp.clean(""), "")

    def test_none_like_whitespace_returns_empty(self):
        self.assertEqual(self.pp.clean("   "), "")

    def test_removes_stopwords(self):
        result = self.pp.clean("I am a software engineer")
        self.assertNotIn("i", result.split())

    def test_lowercases_output(self):
        result = self.pp.clean("Python Java AWS")
        self.assertEqual(result, result.lower())

    def test_preserves_meaningful_tokens(self):
        result = self.pp.clean("machine learning python tensorflow")
        for term in ["machine", "learn", "python", "tensorflow"]:
            self.assertIn(term, result)

    def test_handles_special_characters(self):
        result = self.pp.clean("C++, JavaScript, Node.js")
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# SimilarityScorer Tests
# ---------------------------------------------------------------------------

class TestSimilarityScorer(unittest.TestCase):
    def setUp(self):
        from similarity_scorer import SimilarityScorer
        self.scorer = SimilarityScorer()

    def test_identical_texts_score_near_100(self):
        text = "experienced python developer machine learning nlp"
        score = self.scorer.compute_score(text, text)
        self.assertGreater(score, 90.0)

    def test_score_range_0_to_100(self):
        score = self.scorer.compute_score(
            "python developer backend",
            "chef cooking restaurant kitchen",
        )
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_empty_resume_raises(self):
        from similarity_scorer import ValidationError
        with self.assertRaises(ValidationError):
            self.scorer.compute_score("", "some job description")

    def test_empty_jd_raises(self):
        from similarity_scorer import ValidationError
        with self.assertRaises(ValidationError):
            self.scorer.compute_score("some resume text", "")

    def test_get_skill_sets_intersection(self):
        resume = {"python", "sql", "java"}
        jd = {"python", "sql", "aws", "docker"}
        matched, missing = self.scorer.get_skill_sets(resume, jd)
        self.assertEqual(matched, {"python", "sql"})
        self.assertEqual(missing, {"aws", "docker"})

    def test_get_skill_sets_no_overlap(self):
        matched, missing = self.scorer.get_skill_sets({"java"}, {"python"})
        self.assertEqual(matched, set())
        self.assertEqual(missing, {"python"})

    def test_get_skill_sets_full_match(self):
        skills = {"python", "aws"}
        matched, missing = self.scorer.get_skill_sets(skills, skills)
        self.assertEqual(matched, skills)
        self.assertEqual(missing, set())


# ---------------------------------------------------------------------------
# SuggestionEngine Tests
# ---------------------------------------------------------------------------

class TestSuggestionEngine(unittest.TestCase):
    def setUp(self):
        from suggestion_engine import SuggestionEngine
        self.engine = SuggestionEngine(use_llm_fallback=False)

    def test_returns_list(self):
        result = self.engine.generate({"docker", "kubernetes"}, 45.0)
        self.assertIsInstance(result, list)

    def test_mentions_missing_skill(self):
        result = self.engine.generate({"kubernetes"}, 30.0)
        combined = " ".join(result).lower()
        self.assertIn("kubernetes", combined)

    def test_low_score_triggers_rewrite_advice(self):
        result = self.engine.generate(set(), 20.0)
        combined = " ".join(result).lower()
        self.assertTrue(
            any(kw in combined for kw in ["rewrite", "summary", "below", "ats"])
        )

    def test_high_score_gives_polish_advice(self):
        result = self.engine.generate(set(), 85.0)
        combined = " ".join(result).lower()
        self.assertTrue(
            any(kw in combined for kw in ["strong", "format", "linkedin", "polish"])
        )

    def test_empty_missing_skills_no_crash(self):
        result = self.engine.generate(set(), 75.0)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_at_least_min_suggestions(self):
        result = self.engine.generate({"python", "aws", "docker"}, 35.0)
        self.assertGreaterEqual(len(result), 3)


# ---------------------------------------------------------------------------
# PDFParser Tests (mocked pdfplumber)
# ---------------------------------------------------------------------------

class TestPDFParser(unittest.TestCase):
    def setUp(self):
        from pdf_parser import PDFParser
        self.parser = PDFParser()

    def test_none_input_raises(self):
        from pdf_parser import PDFParseError
        with self.assertRaises(PDFParseError):
            self.parser.extract(None)

    @patch("pdf_parser.pdfplumber.open")
    def test_empty_pdf_raises(self, mock_open):
        from pdf_parser import PDFParseError
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf
        with self.assertRaises(PDFParseError):
            self.parser.extract("fake.pdf")

    @patch("pdf_parser.pdfplumber.open")
    def test_valid_pdf_returns_text(self, mock_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "John Doe Software Engineer Python"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf
        result = self.parser.extract("resume.pdf")
        self.assertIn("Python", result)


# ---------------------------------------------------------------------------
# Orchestrator Integration Tests
# ---------------------------------------------------------------------------

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        from orchestrator import Orchestrator
        self.orch = Orchestrator()

    def test_both_inputs_missing_returns_error(self):
        result = self.orch.analyze(None, "")
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["match_score"])

    def test_missing_jd_returns_error(self):
        result = self.orch.analyze("some resume text", "")
        self.assertIsNotNone(result["error"])

    def test_missing_resume_returns_error(self):
        result = self.orch.analyze(None, "some job description")
        self.assertIsNotNone(result["error"])

    def test_plain_text_resume_full_pipeline(self):
        resume = (
            "Experienced Python developer with 3 years of experience in "
            "machine learning, NLP, and REST API development. "
            "Proficient in TensorFlow, scikit-learn, and spaCy."
        )
        jd = (
            "We are looking for a Python developer with NLP experience. "
            "Knowledge of machine learning frameworks such as TensorFlow or "
            "PyTorch is required. Experience with REST APIs is a plus."
        )
        result = self.orch.analyze(resume, jd)
        self.assertIsNone(result["error"])
        self.assertIsNotNone(result["match_score"])
        self.assertGreaterEqual(result["match_score"], 0.0)
        self.assertLessEqual(result["match_score"], 100.0)
        self.assertIsInstance(result["matched_skills"], set)
        self.assertIsInstance(result["missing_skills"], set)
        self.assertIsInstance(result["suggestions"], list)

    def test_result_keys_present(self):
        result = self.orch.analyze("python developer", "software engineer python")
        for key in ("match_score", "matched_skills", "missing_skills", "suggestions", "error"):
            self.assertIn(key, result)

    def test_similar_texts_score_above_50(self):
        text = "Python machine learning NLP scikit-learn data science"
        result = self.orch.analyze(text, text + " tensorflow")
        self.assertIsNone(result["error"])
        self.assertGreater(result["match_score"], 50.0)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [
        TestPreprocessor,
        TestSimilarityScorer,
        TestSuggestionEngine,
        TestPDFParser,
        TestOrchestrator,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
