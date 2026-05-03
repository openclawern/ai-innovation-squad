# Exam Paper Analyzer — 15-Minute Presentation

**MOE O-Level History Specimen Paper Analysis Tool**  
Candidate: Ern | GovTech AI Innovation Squad Take-Home Assessment

---

## Slide 1 — Problem Statement

**MOE needs to efficiently verify:**
1. Does this exam paper cover all syllabus objectives?
2. Is the mark allocation balanced across topics?
3. Is the cognitive demand appropriate for the level?

**Current process:** Manual review by senior educators → time-consuming, subjective, no audit trail

**Proposed solution:** AI tool that analyses any exam PDF against any syllabus PDF and produces a structured report in seconds.

---

## Slide 2 — Demo

[Live demo / screenshots]

**Inputs:**
- Upper Secondary History Syllabus 2174 (PDF)
- O-Level History Specimen Paper 2174/01 (PDF)

**Outputs:**
- Alignment Score: **82/100**
- Balance Score: **75/100**
- Question-by-question Bloom's taxonomy tagging
- Topic weightage chart (doughnut)
- Covered vs. missing objectives
- Specific recommendations

---

## Slide 3 — Architecture

```
User uploads 2 PDFs
        │
        ▼
FastAPI backend
        │
        ├── PDF Extraction
        │   ├── pdfplumber (text-based PDFs)
        │   └── Tesseract OCR (image-based PDFs)
        │
        ├── LLM Analysis
        │   ├── Claude Haiku (primary — fast, cheap)
        │   ├── GPT-4o Mini (alternative)
        │   └── Demo mode (offline fallback)
        │
        └── Results Dashboard
            ├── Chart.js visualizations
            ├── Question breakdown table
            └── JSON API for integration
```

**Key design choice:** LLM-based semantic analysis vs. keyword matching
- Keywords miss paraphrasing, conflate similar terms
- LLMs understand intent — "examine causes" maps to AO3 correctly
- Structured JSON output enforced via prompt engineering

---

## Slide 4 — Demo Results (O-Level History 2174/01)

**Alignment Score: 82/100**
- ✅ AO2 (source handling): all of Section A directly tests this
- ✅ AO3 (substantiated judgements): Q1e and all Section B essays
- ✅ AO1 (knowledge): required for contextualisation throughout
- ⚠️ Gap: social/economic dimensions of colonial rule not tested
- ⚠️ Gap: specific local resistance narratives not covered

**Balance Score: 75/100**
- Section A (30 marks, 43%): entirely on Appeasement / Europe in Crisis
- Section B (40 marks, 57%): SEA topics — European expansion + challenges
- Reasonable split given paper structure; no single topic dominates

**Bloom's Distribution**
- Evaluate: 35% | Analyze: 35% | Apply: 15% | Understand: 10% | Remember: 5%
- Appropriately weighted for GCE O-Level (high-order thinking emphasis)

---

## Slide 5 — Evaluation Framework

**Why evaluate?** LLMs can hallucinate — we need to know when to trust the output.

**Metrics:**

| Metric | Result | Interpretation |
|--------|--------|----------------|
| Marks Accuracy | 100% | Predicted marks match ground truth exactly |
| Bloom's Exact Agreement | 78% | 7/9 questions correctly tagged |
| Bloom's Adjacent Agreement | 100% | All predictions within 1 Bloom's level |
| Covered Objectives Recall | 80% | Most objectives correctly identified |
| Missing Objectives Recall | 100% | All gaps correctly flagged |
| Factual Consistency | ✅ Pass | Marks sum, percentages internally consistent |
| **Overall Score** | **89.5/100** | Strong performance on this paper |

**Caveat:** Ground truth is manually constructed for this demo — a production evaluation would need a labelled dataset from domain experts.

---

## Slide 6 — Evaluation Design Choices

**Soft/fuzzy matching for objectives:**  
Syllabus objectives are paraphrased — exact string match systematically undercounts correct answers. Fuzzy word overlap (≥2 common words) is pragmatic.

**Adjacent Bloom's agreement:**  
Analyse vs Evaluate is genuinely ambiguous — experienced educators disagree. Adjacent agreement is more meaningful than exact match alone.

**What's not yet measured:**
- Quality of narrative recommendations (would use LLM-as-judge)
- Comparison across multiple papers over time
- User satisfaction / actionability of output

---

## Slide 7 — Next Steps

**Short term (1–2 weeks):**
1. Build labelled dataset: 3 educators tag 20 past papers → majority vote ground truth
2. A/B test model choice (Haiku vs Sonnet vs GPT-4o) on accuracy vs. cost
3. Add PDF export (shareable report for paper setters)

**Medium term (1–3 months):**
4. Batch analysis: compare alignment trends across years
5. Diff view: show changes between consecutive exam papers
6. Auth layer for government intranet deployment
7. Integration with MOE's existing curriculum management systems

**Production considerations:**
- Model: Claude Sonnet for production quality; Haiku for cost-efficient screening
- Data privacy: run on-premises or via GovTech-approved cloud with data residency
- Audit trail: log all analyses with timestamps for accountability
- Human-in-loop: tool surfaces issues; final decision stays with educators

---

## Slide 8 — Q&A

**Anticipated questions:**

_Q: Why not just use ChatGPT directly?_  
A: Structured JSON output, controlled prompt, reproducible results, audit trail, and no data leaving approved infrastructure.

_Q: How do you handle subject areas where you don't have ground truth?_  
A: Evaluation bootstraps with educator annotation. The tool is useful even without ground truth — the value is in surfacing structured information for human review, not making autonomous decisions.

_Q: What if the LLM gets it wrong?_  
A: Factual consistency checks catch obvious errors. Bloom's adjacent agreement shows errors are near-misses, not wild hallucinations. Evaluation score of 89.5% gives confidence for use as a first-pass screening tool.

_Q: Could this replace curriculum designers?_  
A: No — and it shouldn't. The tool handles the tedious structured extraction; educators apply domain judgment. Augmentation, not replacement.
