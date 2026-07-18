from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "normalized_structured"
ENRICHED_DIR = PROJECT_ROOT / "data" / "enriched_structured_priority"
OUTPUT_PATH = PROJECT_ROOT / "data" / "catalog" / "manual_review_queue.json"
CONFIDENCE_THRESHOLD = 0.72


def main() -> None:
    queue: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    total = 0

    for normalized_path in sorted(NORMALIZED_DIR.glob("*_normalized_structured.json")):
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        code = normalized.get("source", {}).get("procedure_code")
        if not code:
            continue

        total += 1
        enriched_path = ENRICHED_DIR / f"{code.replace('.', '_')}_enriched_structured.json"
        enriched = json.loads(enriched_path.read_text(encoding="utf-8")) if enriched_path.exists() else None

        review = evaluate_for_review(normalized, enriched)
        if not review["needs_manual_review"]:
            continue

        queue.append(
            {
                "procedure_code": code,
                "title": normalized.get("source", {}).get("title"),
                "field": normalized.get("source", {}).get("field"),
                "confidence_score": review["confidence_score"],
                "reasons": review["reasons"],
                "normalized_path": str(normalized_path),
                "enriched_path": str(enriched_path) if enriched_path.exists() else None,
            }
        )
        reason_counter.update(review["reasons"])

    queue.sort(key=lambda item: (item["confidence_score"], item["procedure_code"]))
    payload = {
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "total_checked": total,
        "manual_review_count": len(queue),
        "manual_review_ratio": round(len(queue) / total, 4) if total else 0.0,
        "top_reasons": [{"reason": reason, "count": count} for reason, count in reason_counter.most_common(12)],
        "queue": queue,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "total_checked": total,
                "manual_review_count": len(queue),
                "output_path": str(OUTPUT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def evaluate_for_review(normalized: dict[str, Any], enriched: dict[str, Any] | None) -> dict[str, Any]:
    score = 1.0
    reasons: list[str] = []
    signals = normalized.get("signals", {})
    documents = normalized.get("documents", {})
    submission = normalized.get("submission", {})

    warning_count = len(signals.get("raw_parse_warnings") or [])
    if warning_count:
        score -= min(0.24, warning_count * 0.08)
        reasons.append("raw_parse_warnings_present")

    if signals.get("missing_documents"):
        score -= 0.25
        reasons.append("missing_documents")

    if signals.get("missing_results"):
        score -= 0.15
        reasons.append("missing_results")

    if not submission.get("channels"):
        score -= 0.12
        reasons.append("missing_submission_channels")

    document_count = int(documents.get("document_count") or 0)
    if document_count == 0:
        score -= 0.10
        reasons.append("document_count_zero")

    if not submission.get("timing_summary", {}).get("unique_processing_times"):
        score -= 0.06
        reasons.append("processing_time_missing")

    if enriched is None:
        score -= 0.20
        reasons.append("enriched_output_missing")
    else:
        guidance = enriched.get("guidance", {})
        intake = enriched.get("intake", {})
        experience = enriched.get("experience", {})
        provenance = enriched.get("provenance", {})

        if not provenance.get("supported_group"):
            score -= 0.12
            reasons.append("unsupported_group")
        if not guidance.get("validation_hints"):
            score -= 0.05
            reasons.append("validation_hints_missing")
        if not intake.get("candidate_input_fields"):
            score -= 0.10
            reasons.append("candidate_input_fields_missing")
        if not experience.get("overview_summary"):
            score -= 0.08
            reasons.append("overview_summary_missing")

    score = max(0.0, round(score, 2))
    return {
        "confidence_score": score,
        "needs_manual_review": score < CONFIDENCE_THRESHOLD,
        "reasons": reasons,
    }


if __name__ == "__main__":
    main()
