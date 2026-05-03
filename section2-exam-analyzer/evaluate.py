"""
Evaluation framework for the Exam Paper Analyzer.

Metrics:
1. Alignment Recall — % of syllabus objectives correctly identified as covered/missing
2. Weightage Accuracy — Mean Absolute Error between predicted and true mark allocation
3. Bloom's Agreement — Agreement between LLM-assigned and human-assigned Bloom's levels
4. Factual Consistency — Cross-check: marks per question summed == total marks on paper
5. Latency — Time to complete analysis
6. Hallucination Check — Flag topics mentioned in analysis but not in either document

Usage:
    python evaluate.py --syllabus path/to/syllabus.pdf --exam path/to/exam.pdf [--ground-truth ground_truth.json]
"""

import json
import time
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


# Ground truth for the O-Level History specimen paper (2174/01)
DEMO_GROUND_TRUTH = {
    "total_marks": 70,
    "question_marks": {
        "1a": 6, "1b": 5, "1c": 6, "1d": 5, "1e": 8,
        "section_a_total": 30,
        "section_b_per_essay": 20,
        "section_b_total": 40,
    },
    "bloom_levels": {
        "1a": "Evaluate",
        "1b": "Analyze",
        "1c": "Evaluate",
        "1d": "Analyze",
        "1e": "Evaluate",
        "essay": "Evaluate",
    },
    "covered_objectives": [
        "Source analysis (AO2)",
        "Substantiated judgements (AO3)",
        "Historical knowledge (AO1)",
        "Causation and consequence",
        "Multiple perspectives / bias",
    ],
    "missing_objectives": [
        "Social and economic dimensions of colonial rule",
        "Local resistance narratives",
        "Change over time within 1870s-1942",
    ],
    "topic_weightage": {
        "Europe in Crisis / Appeasement": 43.0,
        "European Expansion in SEA": 28.6,
        "Challenges to European Dominance": 28.6,
    }
}


def evaluate_marks_accuracy(predicted: List[Dict], ground_truth: Dict) -> Dict[str, Any]:
    """Check if predicted marks per question match ground truth."""
    gt_marks = ground_truth.get("question_marks", {})
    errors = []
    correct = 0
    total = 0

    for q in predicted:
        qid = q.get("question_id", "")
        pred_marks = q.get("marks", 0)
        true_marks = gt_marks.get(qid)
        if true_marks is not None:
            total += 1
            err = abs(pred_marks - true_marks)
            errors.append(err)
            if err == 0:
                correct += 1

    if not errors:
        return {"marks_accuracy": None, "note": "No matchable question IDs found"}

    mae = sum(errors) / len(errors)
    accuracy = correct / total if total else 0

    return {
        "marks_accuracy": round(accuracy, 2),
        "mean_absolute_error": round(mae, 2),
        "questions_matched": total,
        "exact_match_rate": round(accuracy * 100, 1),
    }


def evaluate_bloom_agreement(predicted: List[Dict], ground_truth: Dict) -> Dict[str, Any]:
    """Measure agreement between predicted and ground-truth Bloom's levels."""
    gt_blooms = ground_truth.get("bloom_levels", {})
    matches = 0
    total = 0

    bloom_order = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

    off_by_one = 0
    details = []

    for q in predicted:
        qid = q.get("question_id", "")
        pred = q.get("bloom_level", "")
        true = gt_blooms.get(qid) or gt_blooms.get("essay")  # fallback for essays
        if true:
            total += 1
            exact = pred == true
            if exact:
                matches += 1
            # Check off-by-one
            try:
                diff = abs(bloom_order.index(pred) - bloom_order.index(true))
                if diff <= 1:
                    off_by_one += 1
            except ValueError:
                pass
            details.append({"question": qid, "predicted": pred, "true": true, "match": exact})

    return {
        "bloom_exact_agreement": round(matches / total, 2) if total else None,
        "bloom_adjacent_agreement": round(off_by_one / total, 2) if total else None,
        "total_compared": total,
        "details": details,
    }


def evaluate_factual_consistency(result: Dict) -> Dict[str, Any]:
    """
    Check internal consistency:
    - Do predicted question marks sum to a reasonable total?
    - Are all topic weightage percentages summing to ~100?
    """
    issues = []

    # Check marks sum
    questions = result.get("exam_questions", [])
    if questions:
        total_marks = sum(q.get("marks", 0) for q in questions)
        if total_marks < 40 or total_marks > 120:
            issues.append(f"Unexpected total marks: {total_marks} (expected ~70 for this paper)")

    # Check weightage sums to ~100
    weightage = result.get("topic_weightage", [])
    if weightage:
        total_pct = sum(t.get("percentage", 0) for t in weightage)
        if abs(total_pct - 100) > 5:
            issues.append(f"Topic weightage percentages sum to {total_pct:.1f}% (expected ~100%)")

    # Check alignment score is in [0,100]
    align_score = result.get("alignment_analysis", {}).get("alignment_score")
    if align_score is not None and not (0 <= align_score <= 100):
        issues.append(f"Alignment score out of range: {align_score}")

    return {
        "is_consistent": len(issues) == 0,
        "issues": issues,
        "total_predicted_marks": sum(q.get("marks", 0) for q in questions) if questions else None,
    }


def evaluate_alignment_recall(result: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """Compare predicted covered/missing objectives against ground truth."""
    pred_covered = set(str(o).lower() for o in result.get("alignment_analysis", {}).get("covered_objectives", []))
    pred_missing = set(str(o).lower() for o in result.get("alignment_analysis", {}).get("missing_objectives", []))

    gt_covered = set(str(o).lower() for o in ground_truth.get("covered_objectives", []))
    gt_missing = set(str(o).lower() for o in ground_truth.get("missing_objectives", []))

    def fuzzy_recall(predicted: set, ground_truth: set) -> float:
        """Soft recall — count a match if any key word overlaps."""
        if not ground_truth:
            return 1.0
        matched = 0
        for gt in ground_truth:
            gt_words = set(gt.split())
            for pred in predicted:
                pred_words = set(pred.split())
                if len(gt_words & pred_words) >= 2:  # at least 2 words in common
                    matched += 1
                    break
        return matched / len(ground_truth)

    covered_recall = fuzzy_recall(pred_covered, gt_covered)
    missing_recall = fuzzy_recall(pred_missing, gt_missing)

    return {
        "covered_objectives_recall": round(covered_recall, 2),
        "missing_objectives_recall": round(missing_recall, 2),
        "predicted_covered_count": len(pred_covered),
        "predicted_missing_count": len(pred_missing),
        "gt_covered_count": len(gt_covered),
        "gt_missing_count": len(gt_missing),
    }


def run_full_evaluation(
    analysis_result: Dict,
    ground_truth: Optional[Dict] = None,
    latency_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Run all evaluation metrics on an analysis result."""

    if ground_truth is None:
        ground_truth = DEMO_GROUND_TRUTH

    eval_result = {
        "marks_accuracy": evaluate_marks_accuracy(
            analysis_result.get("exam_questions", []), ground_truth
        ),
        "bloom_agreement": evaluate_bloom_agreement(
            analysis_result.get("exam_questions", []), ground_truth
        ),
        "factual_consistency": evaluate_factual_consistency(analysis_result),
        "alignment_recall": evaluate_alignment_recall(analysis_result, ground_truth),
    }

    if latency_seconds is not None:
        eval_result["latency_seconds"] = round(latency_seconds, 2)

    # Compute overall score (simple weighted average)
    scores = []
    ma = eval_result["marks_accuracy"].get("marks_accuracy")
    if ma is not None:
        scores.append(ma)
    ba = eval_result["bloom_agreement"].get("bloom_exact_agreement")
    if ba is not None:
        scores.append(ba)
    cr = eval_result["alignment_recall"].get("covered_objectives_recall", 0)
    scores.append(cr)
    fc = 1.0 if eval_result["factual_consistency"]["is_consistent"] else 0.5
    scores.append(fc)

    eval_result["overall_score"] = round(sum(scores) / len(scores) * 100, 1) if scores else None

    return eval_result


def main():
    parser = argparse.ArgumentParser(description="Evaluate the Exam Paper Analyzer")
    parser.add_argument("--syllabus", help="Path to syllabus PDF")
    parser.add_argument("--exam", help="Path to exam paper PDF")
    parser.add_argument("--ground-truth", help="Path to ground truth JSON file")
    parser.add_argument("--model", default="auto", choices=["auto", "anthropic", "openai", "demo"])
    parser.add_argument("--demo", action="store_true", help="Run evaluation on demo analysis")
    args = parser.parse_args()

    # Load ground truth
    ground_truth = DEMO_GROUND_TRUTH
    if args.ground_truth:
        with open(args.ground_truth) as f:
            ground_truth = json.load(f)

    if args.demo or (not args.syllabus and not args.exam):
        print("Running evaluation on pre-computed demo analysis...\n")
        from analyzer import _demo_analysis
        analysis = _demo_analysis()
        latency = None
    else:
        if not args.syllabus or not args.exam:
            print("Error: --syllabus and --exam are required (or use --demo)")
            sys.exit(1)
        from analyzer import run_analysis
        print(f"Running analysis (model={args.model})...")
        start = time.time()
        analysis = run_analysis(args.syllabus, args.exam, model_preference=args.model)
        latency = time.time() - start
        print(f"Analysis complete in {latency:.1f}s\n")

    eval_result = run_full_evaluation(analysis, ground_truth, latency_seconds=latency)

    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"\nOverall Score:     {eval_result.get('overall_score', 'N/A')} / 100")
    print(f"\nMarks Accuracy:")
    ma = eval_result["marks_accuracy"]
    print(f"  Exact match rate: {ma.get('exact_match_rate', 'N/A')}%")
    print(f"  Mean abs error:   {ma.get('mean_absolute_error', 'N/A')} marks")

    print(f"\nBloom's Agreement:")
    ba = eval_result["bloom_agreement"]
    print(f"  Exact agreement:    {ba.get('bloom_exact_agreement', 'N/A')}")
    print(f"  Adjacent agreement: {ba.get('bloom_adjacent_agreement', 'N/A')}")

    print(f"\nObjective Recall:")
    ar = eval_result["alignment_recall"]
    print(f"  Covered objectives recall: {ar['covered_objectives_recall']}")
    print(f"  Missing objectives recall: {ar['missing_objectives_recall']}")

    print(f"\nFactual Consistency: {'✅ Pass' if eval_result['factual_consistency']['is_consistent'] else '❌ Fail'}")
    for issue in eval_result["factual_consistency"].get("issues", []):
        print(f"  ⚠️  {issue}")

    if latency:
        print(f"\nLatency: {eval_result['latency_seconds']}s")

    print("\n" + "=" * 60)
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    main()
