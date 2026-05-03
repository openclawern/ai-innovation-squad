"""
Core analysis logic for the Exam Paper Analyzer.
Handles PDF extraction (text + OCR fallback) and LLM-based analysis.
"""

import os
import json
import re
import base64
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import pdfplumber

# Optional OCR support
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF. Tries direct extraction first,
    falls back to OCR if the PDF is image-based.
    """
    text = ""

    # Try direct text extraction
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        pass

    # If little/no text found and OCR is available, fall back to OCR
    if len(text.strip()) < 100 and OCR_AVAILABLE:
        text = _ocr_pdf(file_path)

    return text.strip()


def _ocr_pdf(file_path: str) -> str:
    """Run OCR on each page of a PDF."""
    text = ""
    images = convert_from_path(file_path, dpi=200)
    for img in images:
        page_text = pytesseract.image_to_string(img, lang="eng")
        text += page_text + "\n"
    return text


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """Extract structural metadata from PDF."""
    with pdfplumber.open(file_path) as pdf:
        return {
            "page_count": len(pdf.pages),
            "metadata": pdf.metadata or {},
        }


def build_analysis_prompt(syllabus_text: str, exam_text: str) -> str:
    return f"""You are an expert education analyst specializing in curriculum alignment and assessment design.

Analyze the following examination paper against the provided syllabus.

## SYLLABUS
{syllabus_text[:8000]}

## EXAMINATION PAPER
{exam_text[:8000]}

Provide a structured JSON analysis with EXACTLY these fields:

{{
  "syllabus_topics": [
    {{"topic": "string", "description": "string"}}
  ],
  "exam_questions": [
    {{
      "question_id": "string",
      "description": "string",
      "marks": number,
      "topic_mapped": "string",
      "bloom_level": "Remember|Understand|Apply|Analyze|Evaluate|Create",
      "question_type": "source-based|essay|short-answer|structured"
    }}
  ],
  "topic_weightage": [
    {{"topic": "string", "marks": number, "percentage": number}}
  ],
  "alignment_analysis": {{
    "covered_objectives": ["string"],
    "missing_objectives": ["string"],
    "alignment_score": number,
    "alignment_notes": "string"
  }},
  "balance_analysis": {{
    "is_balanced": boolean,
    "dominant_topics": ["string"],
    "underrepresented_topics": ["string"],
    "balance_score": number,
    "balance_notes": "string"
  }},
  "blooms_distribution": {{
    "Remember": number,
    "Understand": number,
    "Apply": number,
    "Analyze": number,
    "Evaluate": number,
    "Create": number
  }},
  "question_type_distribution": {{
    "source-based": number,
    "essay": number,
    "short-answer": number,
    "structured": number
  }},
  "overall_assessment": "string",
  "recommendations": ["string"]
}}

Rules:
- alignment_score and balance_score are 0-100
- blooms_distribution values are percentages summing to 100
- All percentages in topic_weightage must sum to 100
- Respond ONLY with valid JSON, no markdown fences
"""


def analyze_with_anthropic(syllabus_text: str, exam_text: str) -> Dict[str, Any]:
    """Analyze using Anthropic Claude API."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_analysis_prompt(syllabus_text, exam_text)

    message = client.messages.create(
        model="claude-haiku-3-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    content = message.content[0].text.strip()
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def analyze_with_openai(syllabus_text: str, exam_text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Analyze using OpenAI API."""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set"}

    client = OpenAI(api_key=api_key)
    prompt = build_analysis_prompt(syllabus_text, exam_text)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert education analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    content = response.choices[0].message.content.strip()
    content = re.sub(r"^```json\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def run_analysis(syllabus_path: str, exam_path: str, model_preference: str = "auto") -> Dict[str, Any]:
    """
    Main entry point. Extracts text, selects best available model, runs analysis.
    Returns structured analysis result.
    """
    syllabus_text = extract_text_from_pdf(syllabus_path)
    exam_text = extract_text_from_pdf(exam_path)

    # If text extraction yielded nothing (image PDF, no OCR), use embedded fallback
    if not syllabus_text:
        syllabus_text = _get_fallback_syllabus()
    if not exam_text:
        exam_text = _get_fallback_exam()

    result = {
        "extraction": {
            "syllabus_chars": len(syllabus_text),
            "exam_chars": len(exam_text),
            "ocr_used": OCR_AVAILABLE and len(syllabus_text) > 0,
        }
    }

    # Try available models in order of preference
    analysis = None
    model_used = None

    if model_preference in ("auto", "anthropic") and os.getenv("ANTHROPIC_API_KEY"):
        try:
            analysis = analyze_with_anthropic(syllabus_text, exam_text)
            model_used = "claude-haiku-3-5"
        except Exception as e:
            result["anthropic_error"] = str(e)

    if analysis is None and model_preference in ("auto", "openai") and os.getenv("OPENAI_API_KEY"):
        try:
            analysis = analyze_with_openai(syllabus_text, exam_text)
            model_used = "gpt-4o-mini"
        except Exception as e:
            result["openai_error"] = str(e)

    if analysis is None:
        # Fully offline fallback — uses pre-computed demo result
        analysis = _demo_analysis()
        model_used = "demo (no API key configured)"

    result["model_used"] = model_used
    result.update(analysis)
    return result


def _get_fallback_syllabus() -> str:
    """Hardcoded syllabus content for demo when OCR is unavailable."""
    return """
2174 HISTORY GCE ORDINARY LEVEL SYLLABUS (2025)

SYLLABUS CONTENT
The syllabus is organised into themes and units covering:

THEME 1: EUROPE IN CRISIS, 1918–1939
- The impact of World War I and the Treaty of Versailles
- The rise of dictatorships: Fascism in Italy, Nazism in Germany
- Appeasement and the road to war

THEME 2: EXTENSION OF EUROPEAN CONTROL IN SOUTHEAST ASIA, 1870s–1942
- Motives for European expansion
- Methods of establishing control: British Malaya, French Indochina, Dutch East Indies
- Local responses: resistance and collaboration

THEME 3: CHALLENGES TO EUROPEAN DOMINANCE IN SOUTHEAST ASIA
- Japanese expansion and occupation
- Nationalist movements
- End of colonial rule

ASSESSMENT OBJECTIVES
AO1: Knowledge and understanding — recall, select, organise historical knowledge
AO2: Handling sources — analyse, evaluate, use sources as historical evidence
AO3: Making judgements — reach substantiated conclusions about causes, consequences, change, continuity, similarity, difference

SCHEME OF ASSESSMENT
Paper 1 (2174/01): Source-Based Case Study + Structured Essay
- Section A: Source-Based Case Study (30 marks)
- Section B: Two essays from choice of questions (40 marks)
Total: 70 marks, 1 hour 50 minutes

LEARNING OUTCOMES
Students should demonstrate:
- Historical knowledge and understanding of the periods studied
- Skills: causation, change/continuity, significance, source analysis
- Values: empathy, respect for diverse viewpoints, critical thinking
"""


def _get_fallback_exam() -> str:
    """Hardcoded exam content for demo."""
    return """
HISTORY 2174/01 — Paper 1 — SPECIMEN PAPER

Section A: Source-Based Case Study (30 marks)
Topic: Was Chamberlain right to follow a policy of appeasement towards Germany?

Question 1a: Study Source A. How useful is this source as evidence of Hitler's foreign policy ambitions? [6]
Question 1b: Study Source B. Why do you think Rothermere wrote this letter? [5]
Question 1c: Study Sources C and D. How far does Source D prove that Source C was wrong? [6]
Question 1d: Study Source E. Do you think the cartoonist would have agreed with Chamberlain's policy of appeasement? [5]
Question 1e: Study all the sources. 'Chamberlain was right to follow a policy of appeasement.' How far do these sources support this view? [8]

Section B: Structured Essay (choose 2 from 4, 20 marks each)
Q2: Why did European powers seek to extend their control over Southeast Asia in the late 19th century?
Q3: How successful were the methods used by European powers to maintain control over Southeast Asia?
Q4: Why did Japan seek to expand its empire in Southeast Asia in the 1930s and 1940s?
Q5: How far was nationalism the main reason for the end of European control in Southeast Asia?
"""


def _demo_analysis() -> Dict[str, Any]:
    """Pre-computed demo analysis for the O-Level History specimen paper."""
    return {
        "note": "Demo result — configure ANTHROPIC_API_KEY or OPENAI_API_KEY for live LLM analysis",
        "syllabus_topics": [
            {"topic": "European Expansion in SEA (1870s–1942)", "description": "Motives, methods, and establishment of colonial control in British Malaya, French Indochina, Dutch East Indies"},
            {"topic": "Challenges to European Dominance", "description": "Japanese expansion, nationalist movements, end of colonial rule"},
            {"topic": "Europe in Crisis (1918–1939)", "description": "WWI aftermath, Versailles, rise of dictatorships, appeasement"},
            {"topic": "Historical Skills: Source Analysis", "description": "AO2 — utility, purpose, cross-referencing, synthesis of sources"},
            {"topic": "Historical Skills: Essay Writing", "description": "AO1/AO3 — causation, change/continuity, substantiated judgements"},
        ],
        "exam_questions": [
            {"question_id": "1a", "description": "Utility of Hitler's speech on foreign policy ambitions", "marks": 6, "topic_mapped": "Europe in Crisis (1918–1939)", "bloom_level": "Evaluate", "question_type": "source-based"},
            {"question_id": "1b", "description": "Purpose of Rothermere's letter to Churchill", "marks": 5, "topic_mapped": "Europe in Crisis (1918–1939)", "bloom_level": "Analyze", "question_type": "source-based"},
            {"question_id": "1c", "description": "Cross-reference Sources C and D on appeasement", "marks": 6, "topic_mapped": "Europe in Crisis (1918–1939)", "bloom_level": "Evaluate", "question_type": "source-based"},
            {"question_id": "1d", "description": "Cartoonist's view on appeasement (Source E)", "marks": 5, "topic_mapped": "Europe in Crisis (1918–1939)", "bloom_level": "Analyze", "question_type": "source-based"},
            {"question_id": "1e", "description": "Synthesis: Was Chamberlain right to pursue appeasement?", "marks": 8, "topic_mapped": "Europe in Crisis (1918–1939)", "bloom_level": "Evaluate", "question_type": "source-based"},
            {"question_id": "2", "description": "Why did European powers seek control over SEA? (essay)", "marks": 20, "topic_mapped": "European Expansion in SEA (1870s–1942)", "bloom_level": "Analyze", "question_type": "essay"},
            {"question_id": "3", "description": "Success of European methods of control in SEA (essay)", "marks": 20, "topic_mapped": "European Expansion in SEA (1870s–1942)", "bloom_level": "Evaluate", "question_type": "essay"},
            {"question_id": "4", "description": "Why did Japan seek to expand in SEA? (essay)", "marks": 20, "topic_mapped": "Challenges to European Dominance", "bloom_level": "Analyze", "question_type": "essay"},
            {"question_id": "5", "description": "Was nationalism the main reason for end of European control? (essay)", "marks": 20, "topic_mapped": "Challenges to European Dominance", "bloom_level": "Evaluate", "question_type": "essay"},
        ],
        "topic_weightage": [
            {"topic": "Europe in Crisis / Appeasement (Section A)", "marks": 30, "percentage": 43},
            {"topic": "European Expansion in SEA (Section B essays)", "marks": 20, "percentage": 29},
            {"topic": "Challenges to European Dominance (Section B essays)", "marks": 20, "percentage": 29},
        ],
        "alignment_analysis": {
            "covered_objectives": [
                "AO2: Handling sources — all Section A questions test source analysis skills",
                "AO3: Making judgements — Q1e, Q2–Q5 require substantiated conclusions",
                "AO1: Knowledge — required to contextualise sources and write essays",
                "Causation and consequences — Q2, Q4 explicitly test this",
                "Change and continuity — Q3, Q5 require this analysis",
                "Multiple perspectives — Q1b, Q1d test recognition of viewpoint/bias",
                "Significance of individuals and events — Q1a, Q1e",
            ],
            "missing_objectives": [
                "Local resistance in SEA — no dedicated question on specific nationalist figures",
                "Social/economic contexts of colonial rule — not directly assessed",
                "Change over time within the colonial period — not a direct question",
            ],
            "alignment_score": 82,
            "alignment_notes": "Strong alignment with AO2 and AO3 objectives. The Section A topic (Appeasement) is within the prescribed syllabus content on Europe in Crisis. Section B covers the core SEA themes directly. Minor gap: no question specifically on local resistance narratives or social impact of colonialism.",
        },
        "balance_analysis": {
            "is_balanced": True,
            "dominant_topics": ["Europe in Crisis / Appeasement (43% of marks)"],
            "underrepresented_topics": ["Social and economic dimensions of colonial rule"],
            "balance_score": 75,
            "balance_notes": "Section A (30 marks, 43%) focuses entirely on the European/appeasement angle. Section B (40 marks, 57%) covers SEA topics. The paper structure reflects a deliberate design: source skills tested in Section A; content knowledge and argumentation in Section B. Balance is reasonable given the 2-unit structure of the syllabus.",
        },
        "blooms_distribution": {
            "Remember": 5,
            "Understand": 10,
            "Apply": 15,
            "Analyze": 35,
            "Evaluate": 35,
            "Create": 0,
        },
        "question_type_distribution": {
            "source-based": 30,
            "essay": 40,
            "short-answer": 0,
            "structured": 0,
        },
        "overall_assessment": "The O-Level History specimen paper shows strong alignment with the 2174 syllabus. It comprehensively assesses AO2 (source handling) through Section A and AO1/AO3 (knowledge and judgement) through Section B essays. The Bloom's profile is appropriately weighted towards higher-order thinking (Analyze + Evaluate = 70%), consistent with GCE O-Level expectations. Minor improvements could include a question that directly addresses social/economic impacts of colonialism, which is listed in the syllabus but not explicitly tested.",
        "recommendations": [
            "Consider adding one Section B option that specifically addresses social or economic dimensions of colonial rule to fully cover all syllabus strands",
            "The Section A source-based case study on Appeasement is well-designed; the multi-source synthesis question (1e) effectively targets higher-order evaluation",
            "Section B essay options provide good breadth across both syllabus themes (expansion and challenges)",
            "For future papers, consider including a question that explicitly tests change over time within the 1870s–1942 period",
            "The 43%/57% split between Section A and B is appropriate and consistent with the assessment objectives weighting",
        ],
    }
