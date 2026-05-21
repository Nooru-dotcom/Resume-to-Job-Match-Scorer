# ResumeAI Pro v2.0 — Resume-to-Job Match Scorer

**Team:** M. Noor ul Hassan (BSCS24088) · Ahmad Hassan (BSCS24140)  
**Course:** Software Engineering

---

## What's New in v2.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Semantic match score | ✅ | ✅ |
| Skill gap analysis | ✅ | ✅ Enhanced |
| Improvement suggestions | ✅ Basic | ✅ 7+ rule types + LLM |
| Custom dark UI | ❌ | ✅ Premium dark theme |
| Score ring visualization | ❌ | ✅ SVG circular progress |
| Skill radar chart | ❌ | ✅ 5-category spider chart |
| ATS simulation | ❌ | ✅ Pass/fail with checklist |
| Keyword density analysis | ❌ | ✅ Top 15 JD keywords |
| Resume rewriter | ❌ | ✅ AI summary rewrite |
| Cover letter generator | ❌ | ✅ Template with tips |
| Multi-job comparison | ❌ | ✅ Up to 3 JDs side-by-side |
| Session history | ❌ | ✅ Last 10 analyses |
| JSON export | ❌ | ✅ Full report download |
| Quantification detector | ❌ | ✅ Warns if no numbers |
| Section detector | ❌ | ✅ Detects missing sections |
| Word count analysis | ❌ | ✅ Length feedback |

---

## Quick Start

### Google Colab
```python
!python setup_colab.py
!python app.py
```

### Local
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python app.py
```

Open: **http://localhost:7860**

---

## Architecture

```
[Custom Gradio UI] → [Orchestrator v2]
    ↓                      ↓
[6 Tabs]          [PDF Parser | Preprocessor | 
                   Skill Extractor | Similarity Scorer |
                   Suggestion Engine v2]
                          ↓
                [Sentence-BERT | spaCy | KeyBERT | pdfplumber]
```

Layered N-Tier architecture. UI calls only `orchestrator.analyze()`.
