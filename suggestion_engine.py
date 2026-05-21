"""
suggestion_engine.py — Layer 3c: Suggestion Engine (v2.1)
Category-aware specific suggestions: frameworks, cloud, DevOps, soft skills,
databases, testing, version control, and more — each with named tools and
actionable next steps, not generic advice.
"""
from __future__ import annotations
import os

_LOW = 40.0
_MID = 70.0

# ── Skill category maps ────────────────────────────────────────────────────────
# Each entry: keyword_fragment → (category_label, named_suggestion)
_FRAMEWORK_MAP = {
    "django":     "Django (Python web framework)",
    "flask":      "Flask (Python micro-framework)",
    "fastapi":    "FastAPI (async Python API framework)",
    "spring":     "Spring Boot (Java framework)",
    "express":    "Express.js (Node.js framework)",
    "rails":      "Ruby on Rails",
    "laravel":    "Laravel (PHP framework)",
    "react":      "React.js (frontend framework)",
    "angular":    "Angular (frontend framework)",
    "vue":        "Vue.js (frontend framework)",
    "nextjs":     "Next.js (full-stack React framework)",
    "next.js":    "Next.js (full-stack React framework)",
    "nestjs":     "NestJS (Node.js backend framework)",
    ".net":       ".NET / ASP.NET",
}

_CLOUD_MAP = {
    "aws":        "AWS",
    "amazon web": "AWS",
    "azure":      "Microsoft Azure",
    "gcp":        "Google Cloud Platform (GCP)",
    "google cloud":"Google Cloud Platform (GCP)",
    "heroku":     "Heroku",
    "vercel":     "Vercel",
    "digitalocean":"DigitalOcean",
    "lambda":     "AWS Lambda (serverless)",
    "ec2":        "AWS EC2",
    "s3":         "AWS S3",
}

_DEVOPS_MAP = {
    "kubernetes": "Kubernetes (K8s)",
    "k8s":        "Kubernetes (K8s)",
    "docker":     "Docker (containerization)",
    "jenkins":    "Jenkins (CI/CD)",
    "github actions": "GitHub Actions (CI/CD)",
    "gitlab ci":  "GitLab CI/CD",
    "terraform":  "Terraform (infrastructure-as-code)",
    "ansible":    "Ansible (configuration management)",
    "helm":       "Helm (Kubernetes package manager)",
    "ci/cd":      "CI/CD pipelines",
    "devops":     "DevOps practices",
}

_DB_MAP = {
    "postgresql": "PostgreSQL",
    "postgres":   "PostgreSQL",
    "mysql":      "MySQL",
    "mongodb":    "MongoDB (NoSQL)",
    "redis":      "Redis (caching/pub-sub)",
    "elasticsearch": "Elasticsearch",
    "cassandra":  "Apache Cassandra",
    "dynamodb":   "AWS DynamoDB",
    "firebase":   "Firebase (Google)",
    "sqlite":     "SQLite",
    "oracle":     "Oracle DB",
    "neo4j":      "Neo4j (graph database)",
}

_SOFTSKILL_MAP = {
    "communication":    "communication",
    "teamwork":         "teamwork and collaboration",
    "leadership":       "leadership",
    "problem solving":  "problem-solving",
    "problem-solving":  "problem-solving",
    "agile":            "Agile methodology",
    "scrum":            "Scrum framework",
    "collaboration":    "cross-functional collaboration",
    "presentation":     "presentation skills",
    "time management":  "time management",
    "critical thinking":"critical thinking",
    "mentoring":        "mentoring/coaching",
}

_TESTING_MAP = {
    "pytest":     "pytest (Python testing)",
    "junit":      "JUnit (Java testing)",
    "jest":       "Jest (JavaScript testing)",
    "selenium":   "Selenium (UI automation)",
    "cypress":    "Cypress (end-to-end testing)",
    "unit test":  "unit testing",
    "tdd":        "Test-Driven Development (TDD)",
    "bdd":        "Behaviour-Driven Development (BDD)",
    "postman":    "Postman (API testing)",
}

_VCS_MAP = {
    "git":        "Git (version control)",
    "github":     "GitHub",
    "gitlab":     "GitLab",
    "bitbucket":  "Bitbucket",
}

_ML_MAP = {
    "tensorflow": "TensorFlow",
    "pytorch":    "PyTorch",
    "scikit":     "scikit-learn",
    "keras":      "Keras",
    "huggingface":"Hugging Face Transformers",
    "bert":       "BERT / Transformer models",
    "openai":     "OpenAI API",
    "langchain":  "LangChain",
    "mlflow":     "MLflow (experiment tracking)",
    "spark":      "Apache Spark (distributed ML)",
}


def _match_category(skill: str, category_map: dict) -> str | None:
    """Return the human-readable name if the skill matches any map key."""
    sl = skill.lower()
    for key, label in category_map.items():
        if key in sl:
            return label
    return None


class SuggestionEngine:
    MIN_SUGGESTIONS = 5

    def __init__(self, use_llm_fallback: bool = True):
        self._use_llm = use_llm_fallback and bool(
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )

    def generate(
        self,
        missing_skills: set[str],
        match_score: float,
        has_quantification: bool = True,
        sections_found: list[str] = None,
        word_count: int = 0,
    ) -> list[str]:

        suggestions = self._rule_based(
            missing_skills, match_score, has_quantification,
            sections_found or [], word_count
        )

        if len(suggestions) < self.MIN_SUGGESTIONS and self._use_llm:
            extras = self._llm_fallback(missing_skills, match_score)
            seen = set(suggestions)
            for s in extras:
                if s not in seen:
                    suggestions.append(s)
                    seen.add(s)

        return suggestions or [
            "Your resume is already well-aligned. "
            "Tailor your summary to mirror the exact language in the job posting."
        ]

    # ── Rule engine ────────────────────────────────────────────────────────────

    def _rule_based(
        self, missing: set[str], score: float,
        has_quant: bool, sections: list[str], wc: int
    ) -> list[str]:

        s: list[str] = []

        # ── 1. FRAMEWORK-SPECIFIC suggestions ─────────────────────────────────
        found_frameworks = []
        for skill in missing:
            label = _match_category(skill, _FRAMEWORK_MAP)
            if label and label not in found_frameworks:
                found_frameworks.append(label)

        for fw in found_frameworks[:3]:
            s.append(
                f"🛠️ **Add {fw} experience to your resume.** "
                f"If you've used it in a side project or coursework, describe it with a "
                f"bullet like: 'Built a REST API using {fw.split('(')[0].strip()}, "
                f"handling X requests/day.' Even personal projects count."
            )

        # ── 2. CLOUD-SPECIFIC suggestions ─────────────────────────────────────
        found_clouds = []
        for skill in missing:
            label = _match_category(skill, _CLOUD_MAP)
            if label and label not in found_clouds:
                found_clouds.append(label)

        if found_clouds:
            cloud_names = ", ".join(found_clouds[:3])
            s.append(
                f"☁️ **Add cloud platform experience ({cloud_names}) to your resume.** "
                f"If you've deployed anything — even a personal project on a free tier — "
                f"mention it explicitly. Cloud certifications (AWS Cloud Practitioner, "
                f"Azure Fundamentals) can substitute for hands-on experience and are "
                f"achievable in 2–4 weeks."
            )

        # ── 3. DEVOPS-SPECIFIC suggestions ────────────────────────────────────
        found_devops = []
        for skill in missing:
            label = _match_category(skill, _DEVOPS_MAP)
            if label and label not in found_devops:
                found_devops.append(label)

        for tool in found_devops[:2]:
            tool_name = tool.split("(")[0].strip()
            s.append(
                f"🚀 **Highlight {tool} knowledge** or consider learning it. "
                f"For {tool_name}: add a bullet point showing you containerized/deployed "
                f"an app, set up a pipeline, or managed infrastructure. "
                f"A small GitHub project demonstrating this speaks volumes to hiring managers."
            )

        # ── 4. DATABASE-SPECIFIC suggestions ──────────────────────────────────
        found_dbs = []
        for skill in missing:
            label = _match_category(skill, _DB_MAP)
            if label and label not in found_dbs:
                found_dbs.append(label)

        if found_dbs:
            db_names = ", ".join(found_dbs[:3])
            s.append(
                f"🗄️ **Mention database experience with {db_names}.** "
                f"Include schema design, query optimisation, or data modelling work "
                f"in your experience bullets. Specify the database by name — "
                f"'Managed a PostgreSQL database' is far stronger than 'used SQL'."
            )

        # ── 5. SOFT SKILLS suggestions ─────────────────────────────────────────
        found_soft = []
        for skill in missing:
            label = _match_category(skill, _SOFTSKILL_MAP)
            if label and label not in found_soft:
                found_soft.append(label)

        if found_soft:
            soft_names = ", ".join(found_soft[:4])
            s.append(
                f"🤝 **Mention {soft_names} skills explicitly** — don't assume they're "
                f"implied. Add a line in your summary like: 'Strong {found_soft[0]} "
                f"skills demonstrated through leading cross-functional teams.' "
                f"Back it up with a concrete example in your experience section."
            )

        # ── 6. TESTING-SPECIFIC suggestions ───────────────────────────────────
        found_testing = []
        for skill in missing:
            label = _match_category(skill, _TESTING_MAP)
            if label and label not in found_testing:
                found_testing.append(label)

        if found_testing:
            test_names = ", ".join(found_testing[:3])
            s.append(
                f"🧪 **Add testing experience ({test_names}) to your resume.** "
                f"Mention test coverage percentages, frameworks used, or testing "
                f"strategies you've implemented. e.g., 'Wrote unit tests using pytest "
                f"achieving 85% code coverage.'"
            )

        # ── 7. VERSION CONTROL suggestions ────────────────────────────────────
        found_vcs = []
        for skill in missing:
            label = _match_category(skill, _VCS_MAP)
            if label and label not in found_vcs:
                found_vcs.append(label)

        if found_vcs:
            s.append(
                f"🔀 **Explicitly mention {', '.join(found_vcs)} usage.** "
                f"Include your GitHub profile URL in your resume header and describe "
                f"your workflow: branching strategy, PR reviews, commit practices."
            )

        # ── 8. ML/AI-SPECIFIC suggestions ─────────────────────────────────────
        found_ml = []
        for skill in missing:
            label = _match_category(skill, _ML_MAP)
            if label and label not in found_ml:
                found_ml.append(label)

        if found_ml:
            ml_names = ", ".join(found_ml[:3])
            s.append(
                f"🤖 **Highlight ML/AI experience with {ml_names}.** "
                f"Describe model architecture, dataset size, accuracy metrics, or "
                f"deployment method. e.g., 'Trained a BERT-based classifier achieving "
                f"92% F1-score on a 50K sample dataset.'"
            )

        # ── 9. Fallback: generic for unrecognised missing skills ───────────────
        # Any missing skill that didn't match any category above
        categorised = set()
        for maps in [_FRAMEWORK_MAP, _CLOUD_MAP, _DEVOPS_MAP, _DB_MAP,
                     _SOFTSKILL_MAP, _TESTING_MAP, _VCS_MAP, _ML_MAP]:
            for skill in missing:
                if _match_category(skill, maps):
                    categorised.add(skill)

        uncategorised = [sk for sk in sorted(missing) if sk not in categorised]
        for skill in uncategorised[:4]:
            s.append(
                f"📌 **Add '{skill}'** to your Skills section and demonstrate it "
                f"in at least one experience or project bullet point."
            )

        # ── 10. Score-band general advice ─────────────────────────────────────
        if score < _LOW:
            s += [
                "🔴 **Critical — match below 40%:** Rewrite your resume summary "
                "to directly address the core JD requirements using its exact language.",
                "Mirror the **exact job title** from the posting in your resume headline "
                "to improve ATS keyword matching immediately.",
                "Restructure your resume to front-load the most relevant experience "
                "— put your strongest alignment points at the very top.",
            ]
        elif score < _MID:
            s += [
                "🟡 **Moderate match (40–70%):** Expand 2–3 projects with specific "
                "tools, frameworks, and measurable outcomes that match the JD.",
                "Copy **exact phrases** from the job description into your bullet points "
                "— ATS systems do literal keyword matching, not semantic understanding.",
            ]
        else:
            s += [
                "🟢 **Strong match (≥70%):** Focus on polishing formatting and "
                "ensuring consistent tense (past tense for previous roles).",
                "Sync your LinkedIn profile with this updated resume — recruiters "
                "cross-check both, and inconsistencies raise red flags.",
            ]

        # ── 11. Quantification check ───────────────────────────────────────────
        if not has_quant:
            s.append(
                "📊 **No numbers detected in your resume.** Add quantified achievements: "
                "'Reduced API latency by 35%', 'Led a team of 8 engineers', "
                "'Delivered 3 features per sprint', 'Grew user base from 0 to 10K'. "
                "Numbers make your impact concrete and memorable."
            )

        # ── 12. Word count check ───────────────────────────────────────────────
        if wc < 200:
            s.append(
                "📝 **Resume too short** (detected ~{} words). "
                "A strong resume should be 400–700 words. Expand your "
                "experience descriptions with tools used, outcomes achieved, "
                "and responsibilities held.".format(wc)
            )
        elif wc > 900:
            s.append(
                "✂️ **Resume may be too long** (~{} words). "
                "Target under 700 words / 1–2 pages. Cut vague filler phrases "
                "('responsible for', 'assisted with') and keep only quantified "
                "impact statements.".format(wc)
            )

        # ── 13. Missing resume sections ───────────────────────────────────────
        expected = {"Experience", "Education", "Skills"}
        found_set = set(sections)
        for sec in expected - found_set:
            s.append(
                f"📋 **No '{sec}' section detected.** Add one with that exact header — "
                f"ATS systems scan for standard section labels and may skip your content "
                f"without them."
            )

        # ── 14. ATS formatting tip ─────────────────────────────────────────────
        s.append(
            "🤖 **ATS formatting tip:** Avoid tables, multi-column layouts, "
            "text boxes, headers/footers, and graphics. Most ATS parsers read "
            "left-to-right, top-to-bottom plain text only. Use a single-column layout "
            "saved as a clean PDF or .docx."
        )

        # ── 15. Extra missing skills summary ──────────────────────────────────
        if len(missing) > 8:
            extra = sorted(missing)[8:13]
            s.append(
                f"💡 **Additional keywords from the JD to work in:** "
                f"{', '.join(extra)}. Even a brief mention in a project description "
                f"can improve your ATS score significantly."
            )

        return s

    # ── LLM fallback ──────────────────────────────────────────────────────────

    def _llm_fallback(self, missing_skills: set[str], score: float) -> list[str]:
        try:
            import anthropic
            client = anthropic.Anthropic()
            missing_str = ", ".join(sorted(missing_skills)) or "none identified"
            prompt = (
                f"A resume has a {score:.1f}% semantic match with a job description. "
                f"Missing skills: {missing_str}.\n\n"
                "Give exactly 3 specific, actionable suggestions. Each must:\n"
                "- Name the exact skill/tool\n"
                "- Say WHERE to add it on the resume (summary, skills section, bullet point)\n"
                "- Give a one-line example of what the bullet/line should say\n"
                "Plain numbered list only. No preamble."
            )
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            lines = [ln.lstrip("0123456789.-) ").strip() for ln in raw.splitlines() if ln.strip()]
            return [ln for ln in lines if len(ln) > 15]
        except Exception:
            return []
