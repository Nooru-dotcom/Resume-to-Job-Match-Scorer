"""
app.py — Resume-to-Job Match Scorer v2.0
Massively upgraded: custom HTML/CSS UI, multi-job comparison, history,
resume rewriter, ATS simulation, radar chart, export, dark mode, and more.
"""

import gradio as gr
import json
import datetime
import re
from orchestrator import Orchestrator

_orchestrator = Orchestrator()

# ── session history stored in-memory ──────────────────────────────────────────
_history: list[dict] = []

# ══════════════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _score_color(score: float) -> str:
    if score >= 75: return "#22c55e"
    if score >= 50: return "#f59e0b"
    return "#ef4444"

def _score_label(score: float) -> str:
    if score >= 75: return "Excellent Match"
    if score >= 50: return "Moderate Match"
    if score >= 30: return "Weak Match"
    return "Poor Match"

def _ats_rating(score: float, missing_count: int) -> tuple[str, str]:
    """Simulate ATS pass/fail decision with reasoning."""
    if score >= 70 and missing_count <= 3:
        return "✅ LIKELY TO PASS ATS", "#22c55e"
    if score >= 50 and missing_count <= 6:
        return "⚠️ MAY PASS ATS", "#f59e0b"
    return "❌ LIKELY FILTERED BY ATS", "#ef4444"

def _build_radar_html(categories: dict[str, float]) -> str:
    """Build an SVG radar/spider chart for skill category scores."""
    import math
    keys = list(categories.keys())
    vals = list(categories.values())
    n = len(keys)
    if n < 3:
        return ""
    cx, cy, r = 160, 160, 120
    points_outer, points_data = [], []
    for i, v in enumerate(vals):
        angle = math.pi / 2 - (2 * math.pi * i / n)
        ox = cx + r * math.cos(angle)
        oy = cy - r * math.sin(angle)
        points_outer.append((ox, oy))
        dr = r * (v / 100)
        dx = cx + dr * math.cos(angle)
        dy = cy - dr * math.sin(angle)
        points_data.append((dx, dy))

    grid_svgs = ""
    for level in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(n):
            angle = math.pi / 2 - (2 * math.pi * i / n)
            px = cx + r * level * math.cos(angle)
            py = cy - r * level * math.sin(angle)
            pts.append(f"{px:.1f},{py:.1f}")
        grid_svgs += f'<polygon points="{" ".join(pts)}" fill="none" stroke="#334155" stroke-width="1" opacity="0.5"/>'

    axis_svgs = ""
    for ox, oy in points_outer:
        axis_svgs += f'<line x1="{cx}" y1="{cy}" x2="{ox:.1f}" y2="{oy:.1f}" stroke="#334155" stroke-width="1" opacity="0.5"/>'

    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points_data)
    data_svg = f'<polygon points="{data_pts}" fill="#6366f1" fill-opacity="0.35" stroke="#818cf8" stroke-width="2"/>'

    dots = ""
    for x, y in points_data:
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#a5b4fc"/>'

    labels = ""
    for i, (key, val) in enumerate(zip(keys, vals)):
        angle = math.pi / 2 - (2 * math.pi * i / n)
        lx = cx + (r + 22) * math.cos(angle)
        ly = cy - (r + 22) * math.sin(angle)
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#94a3b8">{key}</text>'
        labels += f'<text x="{lx:.1f}" y="{ly + 11:.1f}" text-anchor="middle" font-size="8" fill="#6366f1" font-weight="bold">{val:.0f}%</text>'

    return f"""<svg viewBox="0 0 320 320" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:320px">
{grid_svgs}{axis_svgs}{data_svg}{dots}{labels}
</svg>"""

def _categorize_skills(matched: set, missing: set) -> dict[str, float]:
    """Bucket skills into rough categories and score each bucket."""
    cats = {
        "Programming": ["python","java","javascript","typescript","c++","c#","go","rust","ruby","scala","kotlin","swift"],
        "ML/AI": ["machine learning","deep learning","nlp","tensorflow","pytorch","keras","scikit","bert","transformers","huggingface"],
        "Cloud": ["aws","azure","gcp","docker","kubernetes","terraform","cloud","devops","ci/cd","jenkins"],
        "Data": ["sql","nosql","mongodb","postgresql","spark","hadoop","pandas","numpy","data","analytics","tableau","powerbi"],
        "Soft Skills": ["leadership","communication","teamwork","agile","scrum","project management","collaboration","problem"],
    }
    result = {}
    all_skills = matched | missing
    for cat, keywords in cats.items():
        cat_jd = sum(1 for s in all_skills if any(k in s for k in keywords))
        cat_matched = sum(1 for s in matched if any(k in s for k in keywords))
        if cat_jd > 0:
            result[cat] = round((cat_matched / cat_jd) * 100)
        else:
            result[cat] = 0
    return {k: v for k, v in result.items() if k in result}

def _build_score_ring_html(score: float) -> str:
    """SVG circular progress ring for the main score."""
    color = _score_color(score)
    label = _score_label(score)
    r = 54
    circ = 2 * 3.14159 * r
    dash = (score / 100) * circ
    gap = circ - dash
    return f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:8px">
  <svg width="140" height="140" viewBox="0 0 140 140">
    <circle cx="70" cy="70" r="{r}" fill="none" stroke="#1e293b" stroke-width="12"/>
    <circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="12"
      stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-dashoffset="{circ/4:.1f}"
      stroke-linecap="round" transform="rotate(-90 70 70)"
      style="transition:stroke-dasharray 1s ease"/>
    <text x="70" y="65" text-anchor="middle" font-size="24" font-weight="800" fill="{color}">{score:.0f}%</text>
    <text x="70" y="83" text-anchor="middle" font-size="9" fill="#94a3b8">MATCH SCORE</text>
  </svg>
  <div style="font-size:13px;font-weight:600;color:{color}">{label}</div>
</div>"""

def _build_skills_html(matched: list[str], missing: list[str]) -> str:
    """Build styled skill pill badges."""
    html = '<div style="display:flex;flex-direction:column;gap:16px">'
    
    if matched:
        html += '<div>'
        html += '<div style="font-size:11px;font-weight:600;color:#22c55e;letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">✓ Matched Skills</div>'
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px">'
        for s in matched[:30]:
            html += f'<span style="background:#052e16;color:#4ade80;border:1px solid #166534;border-radius:20px;padding:3px 10px;font-size:11px">{s}</span>'
        html += '</div></div>'

    if missing:
        html += '<div>'
        html += '<div style="font-size:11px;font-weight:600;color:#ef4444;letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px">✗ Missing Skills</div>'
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px">'
        for s in missing[:30]:
            html += f'<span style="background:#2d0909;color:#fca5a5;border:1px solid #7f1d1d;border-radius:20px;padding:3px 10px;font-size:11px">{s}</span>'
        html += '</div></div>'

    html += '</div>'
    return html

def _build_suggestions_html(suggestions: list[str], score: float) -> str:
    """Build numbered suggestion cards with priority icons."""
    icons = ["🚨","⚡","💡","📝","🔧","✨","📌","🎯"]
    colors = ["#ef4444","#f59e0b","#6366f1","#06b6d4","#22c55e","#a855f7","#f97316","#14b8a6"]
    html = '<div style="display:flex;flex-direction:column;gap:10px">'
    for i, s in enumerate(suggestions):
        ic = icons[i % len(icons)]
        col = colors[i % len(colors)]
        html += f'''<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid {col};border-radius:6px;padding:12px 14px;display:flex;gap:12px;align-items:flex-start">
  <span style="font-size:16px;flex-shrink:0">{ic}</span>
  <div>
    <div style="font-size:10px;font-weight:700;color:{col};text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">Priority {i+1}</div>
    <div style="font-size:12px;color:#cbd5e1;line-height:1.55">{s}</div>
  </div>
</div>'''
    html += '</div>'
    return html

def _build_ats_html(score: float, missing_count: int) -> str:
    label, color = _ats_rating(score, missing_count)
    checklist_items = [
        ("Semantic match score ≥ 50%", score >= 50),
        ("Missing skills ≤ 6", missing_count <= 6),
        ("High match (≥ 70%)", score >= 70),
        ("Very few gaps (≤ 3)", missing_count <= 3),
    ]
    items_html = ""
    for text, ok in checklist_items:
        ic = "✅" if ok else "❌"
        items_html += f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;color:#94a3b8">{ic} {text}</div>'
    return f'''<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:16px">
  <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:12px">{label}</div>
  {items_html}
</div>'''

def _build_history_html() -> str:
    if not _history:
        return '<div style="color:#475569;font-size:12px;text-align:center;padding:20px">No analyses yet. Run your first analysis above.</div>'
    rows = ""
    for i, h in enumerate(reversed(_history[-10:])):
        sc = h["score"]
        col = _score_color(sc)
        rows += f'''<div style="display:flex;align-items:center;gap:12px;padding:10px;background:#0f172a;border:1px solid #1e293b;border-radius:6px;margin-bottom:6px">
  <div style="font-size:18px;font-weight:800;color:{col};min-width:48px">{sc:.0f}%</div>
  <div style="flex:1;min-width:0">
    <div style="font-size:11px;color:#e2e8f0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{h["jd_snippet"]}</div>
    <div style="font-size:10px;color:#475569;margin-top:2px">{h["timestamp"]} · {h["matched"]} matched · {h["missing"]} missing</div>
  </div>
  <div style="font-size:10px;color:{col};font-weight:600;white-space:nowrap">{_score_label(sc)}</div>
</div>'''
    return rows

def _rewrite_resume_snippet(resume_text: str, missing_skills: set[str], score: float) -> str:
    """Generate a rewritten resume summary section targeting missing skills."""
    if not missing_skills:
        return "Your resume already covers the key skills. No rewrite needed."
    top_missing = sorted(missing_skills)[:5]
    skills_str = ", ".join(top_missing)
    return f"""**✍️ Suggested Resume Summary Rewrite**

> *Incorporate these missing keywords naturally into your summary/objective section:*

---

**Original approach** → Generic summary that misses JD keywords

**Suggested rewrite template:**

*"Results-driven professional with demonstrated expertise in [{', '.join(sorted(missing_skills)[:3])}]. 
Proven track record of delivering [relevant outcomes]. Skilled in {skills_str} 
with [X] years of experience in [domain]. Seeking to leverage [top skill] capabilities 
to drive impact at [Company Name]."*

---

**💡 Quick wins to add to bullet points:**
{chr(10).join(f"• Mention **{s}** in a specific project or achievement context" for s in top_missing)}

**📊 Current match: {score:.1f}%** — incorporating these keywords could push you to 75%+"""

def _generate_cover_letter_template(jd_text: str, matched: set[str], missing: set[str]) -> str:
    """Generate a targeted cover letter template."""
    top_matched = sorted(matched)[:4]
    top_missing = sorted(missing)[:3]
    today = datetime.date.today().strftime("%B %d, %Y")
    
    return f"""**📝 AI-Generated Cover Letter Template**

---

{today}

Dear Hiring Manager,

I am writing to express my strong interest in this role. With my background in {', '.join(top_matched[:2]) if top_matched else 'the required areas'}, 
I am confident in my ability to contribute meaningfully from day one.

Throughout my career, I have developed expertise in {', '.join(top_matched) if top_matched else 'relevant technologies'}. 
[Add a specific achievement here — quantify with numbers e.g., "reduced processing time by 40%"]

I am particularly excited about the opportunity to apply my skills in {top_matched[0] if top_matched else 'this domain'} 
to [specific aspect of the role/company]. [Add 1-2 sentences about why this company specifically.]

{f"I am actively deepening my knowledge of {', '.join(top_missing)}, which I understand are priorities for this role." if top_missing else ""}

I would welcome the opportunity to discuss how my experience aligns with your team's goals.

Sincerely,
[Your Name]
[Your Email] | [Your Phone] | [LinkedIn URL]

---
*⚡ Tip: Replace all [brackets] with specific details. Quantify every achievement.*"""

def _keyword_density_html(resume_text: str, jd_text: str) -> str:
    """Show top JD keywords and their presence in resume."""
    if not jd_text or not resume_text:
        return ""
    
    # Extract significant words from JD
    stopwords = {"the","a","an","is","are","be","to","of","and","or","in","for","with","on","at","by","this","that","will","can","should","must","we","you","our","your","have","has","from","as","it","its","been","was","were","their","they","all","also","both","each","other","any"}
    jd_words = re.findall(r'\b[a-zA-Z][a-zA-Z+#]{2,}\b', jd_text.lower())
    jd_freq = {}
    for w in jd_words:
        if w not in stopwords:
            jd_freq[w] = jd_freq.get(w, 0) + 1
    top_kw = sorted(jd_freq.items(), key=lambda x: -x[1])[:15]
    
    resume_lower = resume_text.lower()
    rows = ""
    for kw, freq in top_kw:
        in_resume = kw in resume_lower
        count_in_jd = freq
        bar_w = min(100, freq * 12)
        status = '✅' if in_resume else '❌'
        col = '#22c55e' if in_resume else '#ef4444'
        rows += f'''<div style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid #0f172a">
  <div style="font-size:11px;color:#e2e8f0;min-width:110px;font-weight:500">{kw}</div>
  <div style="flex:1;background:#0f172a;border-radius:3px;height:6px">
    <div style="width:{bar_w}%;background:{col};height:6px;border-radius:3px;opacity:0.7"></div>
  </div>
  <div style="font-size:10px;color:#475569;min-width:24px;text-align:right">{count_in_jd}×</div>
  <div style="font-size:12px;min-width:20px">{status}</div>
</div>'''
    return f'<div style="background:#1e293b;border-radius:8px;padding:12px">{rows}</div>'

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

def run_analysis(resume_pdf, resume_text_box: str, job_description: str,
                  job_title: str, company_name: str):
    """Full analysis pipeline returning all UI panel outputs."""
    resume_input = resume_pdf if resume_pdf is not None else resume_text_box.strip()

    if not resume_input and not job_description.strip():
        err = "⚠️ Please provide both a resume and a job description."
        return (err,) + ("",) * 11

    result = _orchestrator.analyze(resume_input, job_description)

    if result["error"]:
        err = f"⚠️ {result['error']}"
        return (err,) + ("",) * 11

    score = result["match_score"]
    matched = sorted(result["matched_skills"])
    missing = sorted(result["missing_skills"])
    suggestions = result["suggestions"]

    # Get raw text for keyword density
    raw_resume = ""
    if resume_pdf:
        try:
            from pdf_parser import PDFParser
            raw_resume = PDFParser().extract(resume_pdf)
        except:
            raw_resume = resume_text_box
    else:
        raw_resume = resume_text_box

    # Save to history
    _history.append({
        "score": score,
        "timestamp": datetime.datetime.now().strftime("%m/%d %H:%M"),
        "jd_snippet": (job_title or job_description[:60]).strip(),
        "matched": len(matched),
        "missing": len(missing),
        "matched_skills": set(matched),
        "missing_skills": set(missing),
        "suggestions": suggestions,
    })

    # Build all output HTML panels
    score_html = _build_score_ring_html(score)
    skills_html = _build_skills_html(matched, missing)
    suggestions_html = _build_suggestions_html(suggestions, score)
    ats_html = _build_ats_html(score, len(missing))
    categories = _categorize_skills(set(matched), set(missing))
    radar_html = _build_radar_html(categories)
    history_html = _build_history_html()
    rewrite_md = _rewrite_resume_snippet(raw_resume, set(missing), score)
    cover_letter_md = _generate_cover_letter_template(job_description, set(matched), set(missing))
    keyword_html = _keyword_density_html(raw_resume, job_description)

    # Stats summary bar
    stats_html = f"""<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
{"".join(f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:10px;text-align:center"><div style="font-size:18px;font-weight:800;color:{c}">{v}</div><div style="font-size:10px;color:#475569;margin-top:3px">{l}</div></div>'
 for v, l, c in [
   (f"{score:.0f}%", "Match Score", _score_color(score)),
   (str(len(matched)), "Matched Skills", "#22c55e"),
   (str(len(missing)), "Skill Gaps", "#ef4444"),
   (str(len(suggestions)), "Suggestions", "#6366f1"),
 ])}
</div>"""

    return (
        score_html,      # score ring
        stats_html,      # stats bar
        skills_html,     # skill pills
        suggestions_html,# suggestions cards
        ats_html,        # ATS simulation
        radar_html,      # radar chart
        history_html,    # history
        rewrite_md,      # resume rewriter
        cover_letter_md, # cover letter
        keyword_html,    # keyword density
        "",              # status
        f"{score:.1f}",  # score for comparison tab
    )

def compare_jobs(resume_pdf, resume_text_box, jd1, jd2, jd3):
    """Compare resume against up to 3 job descriptions."""
    resume_input = resume_pdf if resume_pdf is not None else resume_text_box.strip()
    if not resume_input:
        return "⚠️ Please provide a resume first (use the main Analyse tab).", ""

    results = []
    for idx, jd in enumerate([jd1, jd2, jd3], 1):
        if not jd.strip():
            continue
        r = _orchestrator.analyze(resume_input, jd)
        if not r["error"]:
            results.append((idx, r["match_score"], jd[:60]))

    if not results:
        return "⚠️ Please enter at least one job description.", ""

    results.sort(key=lambda x: -x[1])
    
    bars_html = '<div style="display:flex;flex-direction:column;gap:10px">'
    for rank, (idx, sc, snippet) in enumerate(results, 1):
        col = _score_color(sc)
        bar_w = int(sc)
        medal = ["🥇","🥈","🥉"][rank-1] if rank <= 3 else "  "
        bars_html += f'''<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <div style="font-size:13px;color:#e2e8f0;font-weight:600">{medal} Job {idx}: {snippet}…</div>
    <div style="font-size:16px;font-weight:800;color:{col}">{sc:.1f}%</div>
  </div>
  <div style="background:#1e293b;border-radius:4px;height:8px">
    <div style="width:{bar_w}%;background:{col};height:8px;border-radius:4px;transition:width 1s ease"></div>
  </div>
  <div style="font-size:10px;color:#475569;margin-top:6px">{_score_label(sc)} · {_ats_rating(sc, 5)[0]}</div>
</div>'''
    bars_html += '</div>'

    rec_idx, rec_sc, rec_snip = results[0]
    rec_html = f'<div style="background:#052e16;border:1px solid #166534;border-radius:8px;padding:14px;margin-top:12px"><div style="font-size:12px;font-weight:700;color:#4ade80;margin-bottom:4px">🎯 Best Match: Job {rec_idx}</div><div style="font-size:11px;color:#86efac">Score: {rec_sc:.1f}% — {_score_label(rec_sc)}. This is your strongest alignment. Apply here first.</div></div>'

    return bars_html + rec_html, ""

def export_report(resume_text_box: str, job_description: str) -> str:
    """Export full JSON analysis report."""
    if not _history:
        return "No analysis to export yet."
    last = _history[-1]
    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "match_score": last["score"],
        "score_label": _score_label(last["score"]),
        "ats_prediction": _ats_rating(last["score"], last["missing"])[0],
        "matched_skills": sorted(last["matched_skills"]),
        "missing_skills": sorted(last["missing_skills"]),
        "improvement_suggestions": last["suggestions"],
        "job_snippet": last["jd_snippet"],
    }
    return json.dumps(report, indent=2)

def clear_all():
    return (None, "", "", "", "", "",
            "", "", "", "", "", "", "", "", "")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS — Dark premium theme
# ══════════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --bg-base: #020617;
    --bg-card: #0f172a;
    --bg-elevated: #1e293b;
    --border: #1e293b;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --accent: #6366f1;
    --accent-glow: #818cf8;
}

body, .gradio-container {
    background: var(--bg-base) !important;
    font-family: 'Inter', sans-serif !important;
}

.gradio-container {
    max-width: 1400px !important;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border-bottom: 1px solid #312e81;
    padding: 32px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, #4338ca22 0%, transparent 70%);
    pointer-events: none;
}
.app-header::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 40%;
    height: 200%;
    background: radial-gradient(ellipse, #7c3aed18 0%, transparent 70%);
    pointer-events: none;
}
.header-badge {
    display: inline-block;
    background: #312e81;
    border: 1px solid #4338ca;
    color: #a5b4fc;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 12px;
}
.header-title {
    font-size: 36px;
    font-weight: 900;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
    margin-bottom: 8px;
    font-family: 'Inter', sans-serif;
}
.header-sub {
    font-size: 14px;
    color: #64748b;
    font-weight: 400;
}
.header-team {
    position: absolute;
    top: 28px;
    right: 32px;
    font-size: 11px;
    color: #475569;
    text-align: right;
    line-height: 1.6;
}

/* Tabs */
.tab-nav button {
    background: transparent !important;
    border: none !important;
    color: #475569 !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: all .2s !important;
}
.tab-nav button.selected {
    color: #a5b4fc !important;
    border-bottom-color: #6366f1 !important;
}

/* Panels */
.panel-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}
.panel-label {
    font-size: 11px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Inputs */
textarea, input[type=text] {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color .2s !important;
}
textarea:focus, input[type=text]:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px #6366f118 !important;
    outline: none !important;
}
label span {
    color: #94a3b8 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}

/* Buttons */
.btn-primary {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    padding: 12px 28px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 20px #6366f140 !important;
    transition: all .2s !important;
    letter-spacing: .02em !important;
}
.btn-primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 30px #6366f160 !important;
}
button.secondary {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    color: #94a3b8 !important;
}

/* Markdown output panels */
.output-panel .prose {
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.7;
}
.output-panel h3 {
    color: #a5b4fc;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 10px;
}

/* File upload */
.upload-container {
    border: 2px dashed #1e293b !important;
    border-radius: 10px !important;
    background: #0a0f1e !important;
    transition: border-color .2s !important;
}
.upload-container:hover {
    border-color: #6366f1 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* Section dividers */
.section-title {
    font-size: 13px;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: .1em;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 16px;
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# UI LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

def build_ui() -> gr.Blocks:
    with gr.Blocks(css=CUSTOM_CSS, title="ResumeAI Pro — Match Scorer v2") as demo:

        # ── HEADER ────────────────────────────────────────────────────────────
        gr.HTML("""
<div class="app-header">
  <div class="header-team">
    M. Noor ul Hassan · BSCS24088<br>
    Ahmad Hassan · BSCS24140<br>
    <span style="color:#312e81">Software Engineering</span>
  </div>
  <div class="header-badge">⚡ AI-Powered NLP · v2.0</div>
  <div class="header-title">ResumeAI Pro</div>
  <div class="header-sub">Semantic resume analysis · ATS simulation · Skill gap radar · Cover letter generator · Multi-job comparison</div>
</div>
""")

        # ── TABS ──────────────────────────────────────────────────────────────
        with gr.Tabs(elem_classes=["tab-nav"]):

            # ━━ TAB 1: MAIN ANALYSE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("🔍 Analyse"):
                with gr.Row(equal_height=False):

                    # LEFT: Inputs
                    with gr.Column(scale=4, min_width=340):
                        gr.HTML('<div class="section-title">📥 Resume Input</div>')

                        resume_pdf = gr.File(
                            label="Upload Resume PDF",
                            file_types=[".pdf"],
                            type="filepath",
                            elem_classes=["upload-container"],
                        )
                        gr.HTML('<div style="text-align:center;color:#334155;font-size:11px;padding:4px 0">— or paste text below —</div>')
                        resume_text = gr.Textbox(
                            label="Resume Text",
                            placeholder="Paste your resume content here…",
                            lines=7,
                        )

                        gr.HTML('<div class="section-title" style="margin-top:16px">📋 Job Details</div>')
                        with gr.Row():
                            job_title = gr.Textbox(label="Job Title (optional)", placeholder="e.g. Senior ML Engineer", scale=3)
                            company_name = gr.Textbox(label="Company (optional)", placeholder="e.g. Google", scale=2)
                        jd_input = gr.Textbox(
                            label="Job Description *",
                            placeholder="Paste the full job description here…",
                            lines=9,
                        )

                        with gr.Row():
                            analyse_btn = gr.Button("⚡ Analyse Resume", variant="primary", elem_classes=["btn-primary"], size="lg", scale=3)
                            clear_btn = gr.Button("✕ Clear", size="lg", scale=1)

                        status_out = gr.HTML("")

                    # RIGHT: Outputs
                    with gr.Column(scale=6, min_width=400):

                        # Score + stats row
                        with gr.Row():
                            with gr.Column(scale=2, min_width=160):
                                gr.HTML('<div class="section-title">Score</div>')
                                score_ring = gr.HTML("")
                            with gr.Column(scale=5):
                                gr.HTML('<div class="section-title">Summary</div>')
                                stats_bar = gr.HTML("")

                        gr.HTML('<div class="section-title" style="margin-top:16px">🧠 Skill Analysis</div>')
                        skills_html = gr.HTML("")

                        gr.HTML('<div class="section-title" style="margin-top:16px">💡 Improvement Suggestions</div>')
                        suggestions_html = gr.HTML("")

                        gr.HTML('<div class="section-title" style="margin-top:16px">🤖 ATS Simulation</div>')
                        ats_html = gr.HTML("")

            # ━━ TAB 2: DEEP INSIGHTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("📊 Deep Insights"):
                with gr.Row():
                    with gr.Column(scale=4):
                        gr.HTML('<div class="section-title">🕸️ Skill Category Radar</div>')
                        radar_html = gr.HTML('<div style="color:#475569;font-size:12px;text-align:center;padding:40px">Run an analysis to see the radar chart.</div>')

                    with gr.Column(scale=5):
                        gr.HTML('<div class="section-title">🔑 JD Keyword Density vs. Resume Coverage</div>')
                        keyword_html = gr.HTML('<div style="color:#475569;font-size:12px;text-align:center;padding:40px">Run an analysis to see keyword analysis.</div>')

            # ━━ TAB 3: RESUME TOOLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("✍️ Resume Tools"):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<div class="section-title">🔄 AI Resume Summary Rewriter</div>')
                        rewrite_out = gr.Markdown("*Run an analysis first to generate a rewrite.*")
                    with gr.Column():
                        gr.HTML('<div class="section-title">📝 Cover Letter Generator</div>')
                        cover_letter_out = gr.Markdown("*Run an analysis first to generate a cover letter.*")

            # ━━ TAB 4: MULTI-JOB COMPARE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("⚖️ Compare Jobs"):
                gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:16px">Compare your resume against up to 3 different job descriptions to find your best fit.</div>')
                with gr.Row():
                    jd_compare_1 = gr.Textbox(label="Job Description 1", lines=6, placeholder="Paste JD 1 here…")
                    jd_compare_2 = gr.Textbox(label="Job Description 2", lines=6, placeholder="Paste JD 2 here…")
                    jd_compare_3 = gr.Textbox(label="Job Description 3", lines=6, placeholder="Paste JD 3 here…")
                compare_btn = gr.Button("⚖️ Compare All Jobs", variant="primary", elem_classes=["btn-primary"])
                compare_out = gr.HTML("")
                compare_status = gr.HTML("")

            # ━━ TAB 5: HISTORY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("🕒 History"):
                gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:16px">Your last 10 analyses this session.</div>')
                refresh_hist_btn = gr.Button("🔄 Refresh History", size="sm")
                history_html = gr.HTML('<div style="color:#475569;font-size:12px;text-align:center;padding:20px">No analyses yet.</div>')

            # ━━ TAB 6: EXPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            with gr.Tab("📤 Export"):
                gr.HTML('<div style="color:#64748b;font-size:12px;margin-bottom:16px">Export your latest analysis as a JSON report.</div>')
                export_btn = gr.Button("📥 Generate JSON Report", variant="primary", elem_classes=["btn-primary"])
                export_out = gr.Code(label="Analysis Report (JSON)", language="json", lines=25)

        # ── FOOTER ────────────────────────────────────────────────────────────
        gr.HTML("""
<div style="text-align:center;padding:24px;color:#1e293b;font-size:11px;border-top:1px solid #0f172a;margin-top:24px">
  🔒 All processing is in-memory only. No data is stored or shared with third parties.
  &nbsp;·&nbsp; ResumeAI Pro v2.0 &nbsp;·&nbsp; Built with Sentence-BERT · spaCy · KeyBERT · Gradio
</div>
""")

        # ── WIRE EVENTS ───────────────────────────────────────────────────────

        ANALYSE_OUTPUTS = [
            score_ring, stats_bar, skills_html, suggestions_html,
            ats_html, radar_html, history_html,
            rewrite_out, cover_letter_out, keyword_html, status_out,
            gr.State(),  # internal score state
        ]

        analyse_btn.click(
            fn=run_analysis,
            inputs=[resume_pdf, resume_text, jd_input, job_title, company_name],
            outputs=[score_ring, stats_bar, skills_html, suggestions_html,
                     ats_html, radar_html, history_html,
                     rewrite_out, cover_letter_out, keyword_html, status_out,
                     gr.State()],
        )

        clear_btn.click(
            fn=clear_all,
            inputs=[],
            outputs=[resume_pdf, resume_text, jd_input, job_title, company_name,
                     score_ring, stats_bar, skills_html, suggestions_html,
                     ats_html, radar_html, history_html,
                     rewrite_out, cover_letter_out, status_out],
        )

        compare_btn.click(
            fn=compare_jobs,
            inputs=[resume_pdf, resume_text, jd_compare_1, jd_compare_2, jd_compare_3],
            outputs=[compare_out, compare_status],
        )

        refresh_hist_btn.click(
            fn=lambda: _build_history_html(),
            inputs=[],
            outputs=[history_html],
        )

        export_btn.click(
            fn=export_report,
            inputs=[resume_text, jd_input],
            outputs=[export_out],
        )

    return demo


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        show_error=True,
    )
