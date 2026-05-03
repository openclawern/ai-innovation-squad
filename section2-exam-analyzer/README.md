# Section 2 — Exam Paper Analyzer

An AI-powered tool that analyses examination papers against syllabus objectives, focusing on:
1. **Syllabus alignment** — which learning objectives are covered vs. missing
2. **Topic weightage** — distribution of marks across syllabus topics
3. **Bloom's taxonomy** — cognitive level distribution of questions
4. **Recommendations** — actionable suggestions for improving balance

---

## Installation

```bash
pip install -r requirements.txt
```

**Optional — OCR for image-based PDFs:**
```bash
brew install tesseract
pip install pytesseract pdf2image
```

---

## Running the App

```bash
# With Anthropic Claude (recommended)
ANTHROPIC_API_KEY=your_key python main.py

# With OpenAI
OPENAI_API_KEY=your_key python main.py

# Demo mode (no API key needed)
python main.py
```

Navigate to `http://localhost:8000` and upload:
- A **syllabus PDF** (e.g., Upper Secondary History Syllabus 2174)
- An **examination paper PDF** (e.g., O-Level History Specimen Paper 2174/01)

---

## Architecture

```
User (browser)
    │  POST /analyze (multipart/form-data: syllabus.pdf + exam.pdf)
    ▼
FastAPI (main.py)
    │
    ├── analyzer.py
    │   ├── extract_text_from_pdf()     PDF → text (pdfplumber + OCR fallback)
    │   ├── analyze_with_anthropic()    Claude Haiku → structured JSON
    │   ├── analyze_with_openai()       GPT-4o Mini → structured JSON
    │   └── _demo_analysis()            Offline pre-computed result
    │
    └── templates/results.html          Chart.js visualizations
```

### Design Decisions

**Why LLM for analysis?**
Syllabus-to-question mapping requires semantic understanding — keyword matching misses paraphrased topics and conflates distinct concepts. LLMs handle this naturally and produce structured JSON output that can be rendered directly.

**Why Anthropic Claude Haiku?**
- Fast (< 10s) and cheap (< $0.01 per analysis)
- Excellent instruction-following for structured JSON output
- Strong at curriculum/education domain tasks
- Free-tier via Anthropic API; can substitute any compatible model

**Why FastAPI?**
- Python-native, minimal boilerplate
- Async file uploads
- Easy to extend with new endpoints (e.g., batch analysis, comparison)
- Jinja2 templating for server-side rendering avoids frontend complexity

**PDF Extraction Strategy**
- `pdfplumber` for text-based PDFs (direct text extraction)
- `pytesseract` + `pdf2image` for image-based PDFs (OCR fallback)
- Hardcoded fallback content for demo when neither is available

---

## Evaluation Framework

Run: `python evaluate.py --demo`

### Metrics

| Metric | Description | Demo Result |
|--------|-------------|-------------|
| Marks Accuracy | Exact match rate for predicted vs. true marks per question | 100% |
| Bloom's Exact Agreement | % of questions with correct Bloom's level | 78% |
| Bloom's Adjacent Agreement | % within 1 level of correct | 100% |
| Covered Objectives Recall | Soft-match recall vs. ground truth | 80% |
| Missing Objectives Recall | Soft-match recall for gaps identified | 100% |
| Factual Consistency | Internal consistency check (marks sum, %, ranges) | ✅ Pass |
| **Overall Score** | Weighted average | **89.5 / 100** |

### Evaluation Design Notes

**Why soft/fuzzy matching for objectives?**
Syllabus objectives are described in natural language and an LLM will paraphrase them. Requiring exact string match would systematically undercount correct answers. Fuzzy word overlap (≥2 common words) is a pragmatic middle ground.

**Why Bloom's adjacent agreement?**
Neighbouring Bloom's levels (e.g., Analyze vs Evaluate) are genuinely ambiguous in practice — experienced educators disagree on borderline cases. Adjacent agreement is a more meaningful signal than exact match alone.

**Limitations of the current evaluation**
- Ground truth is manually constructed (no large annotated dataset exists for this paper)
- Soft match for objectives may overcredit vague predictions
- No evaluation of narrative quality in "overall assessment" or "recommendations" fields

### Next Steps for Evaluation
1. Build a labelled dataset: have 3+ educators independently tag 20+ past papers → use majority vote as ground truth
2. Add LLM-as-judge metric: use a second LLM to rate quality of recommendations on a 1–5 scale
3. A/B test: compare analysis quality across models (Haiku vs Sonnet vs GPT-4o) on the labelled dataset
4. Longitudinal: track whether recommendations are acted upon by paper setters

---

## Additional Features Implemented

- **Bloom's taxonomy classification** — automatically tags each question by cognitive level
- **Question type detection** — source-based, essay, structured, short-answer
- **Interactive dashboard** — Chart.js doughnut + bar charts for topic weightage and Bloom's distribution
- **JSON API endpoint** — `/api/analyze` for programmatic access
- **OCR fallback** — handles image-based PDFs when tesseract is installed
- **Multi-model support** — Anthropic, OpenAI, or offline demo mode

---

## Next Steps for Production

1. **Model selection**: Evaluate Claude Sonnet 3.5 vs Haiku vs GPT-4o on accuracy vs cost tradeoff
2. **Batch analysis**: Compare multiple exam papers against same syllabus over time
3. **Diff view**: Show how a new paper's alignment changes vs. previous year
4. **Admin panel**: Allow curriculum designers to tag ground-truth labels for evaluation
5. **Export**: PDF report generation for sharing with paper setters
6. **Access control**: Auth layer if deployed on government intranet
7. **Audit trail**: Log all analyses for accountability
