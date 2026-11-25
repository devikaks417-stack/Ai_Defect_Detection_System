"""
PROMETHEUS-X: INSPECTION ANALYTICS MODULE
File: scripts/inspection_analytics.py
Domain: Automotive Manufacturing Visual Inspection

Implements Feature C: Inspection Analytics & Chart Aggregations
- Maintains persistent session inspection telemetry.
- Calculates summary KPIs (Total inspections, Normal vs Potential Defect, Averages, Max).
- Generates data structures for 4 interactive dashboard charts:
  1. Outcome Distribution (Pie / Donut)
  2. Score Distribution Histogram (Buckets vs Threshold)
  3. Category Benchmark Comparison (Empirical Phase 2.5 scores & detection counts)
  4. Inspection History Chronological Trend
"""

from typing import List, Dict, Any
import numpy as np

# Empirical benchmark data from Phase 2.5 Full Model Evaluation (607 test images)
BENCHMARK_CATEGORIES = [
    {
        "name": "Nominal (good)",
        "code": "good",
        "mean_score": 20.08,
        "samples": 285,
        "detected": 3,
        "auroc": 1.0000,
        "status": "Normal",
        "detection_rate_pct": 1.05  # False positive rate
    },
    {
        "name": "Fastening Wire",
        "code": "fastening",
        "mean_score": 21.79,
        "samples": 277,
        "detected": 10,
        "auroc": 0.7935,
        "status": "Potential Defect",
        "detection_rate_pct": 3.61
    },
    {
        "name": "Blue Hoop",
        "code": "blue_hoop",
        "mean_score": 21.99,
        "samples": 5,
        "detected": 0,
        "auroc": 0.8323,
        "status": "Potential Defect",
        "detection_rate_pct": 0.00
    },
    {
        "name": "Obstruction",
        "code": "obstruction",
        "mean_score": 22.51,
        "samples": 2,
        "detected": 0,
        "auroc": 0.9491,
        "status": "Potential Defect",
        "detection_rate_pct": 0.00
    },
    {
        "name": "Multiple",
        "code": "multiple",
        "mean_score": 23.80,
        "samples": 33,
        "detected": 24,
        "auroc": 0.9712,
        "status": "Potential Defect",
        "detection_rate_pct": 72.73
    },
    {
        "name": "Cardboard",
        "code": "cardboard",
        "mean_score": 31.68,
        "samples": 5,
        "detected": 5,
        "auroc": 1.0000,
        "status": "Potential Defect",
        "detection_rate_pct": 100.00
    }
]

BENCHMARK_KPI = {
    "image_auroc": 0.8165,
    "pixel_auroc": 0.8724,
    "precision": 94.23,
    "recall": 15.22,
    "specificity": 98.95,
    "f1_score": 0.2620,
    "threshold": 23.4457,
    "total_benchmark_images": 607
}

def calculate_analytics_summary(history_records: List[Dict[str, Any]], filter_type: str = "all") -> Dict[str, Any]:
    """
    Computes real-time inspection analytics from the current session history,
    with support for filtering by prediction type.
    
    Args:
        history_records: List of inspection result dicts.
        filter_type: 'all', 'normal', or 'defect'.
        
    Returns:
        Structured analytics dict ready for JSON API serialization.
    """
    th = BENCHMARK_KPI["threshold"]
    total_raw = len(history_records)
    
    # Filter records if requested
    if filter_type == "normal":
        filtered = [r for r in history_records if not r.get("is_anomaly", False) and r.get("anomaly_score", 0) <= th]
    elif filter_type == "defect":
        filtered = [r for r in history_records if r.get("is_anomaly", False) or r.get("anomaly_score", 0) > th]
    else:
        filtered = history_records

    total = len(filtered)
    scores = [r["anomaly_score"] for r in filtered]
    
    # Raw total counts for global doughnut
    raw_normals = sum(1 for r in history_records if not r.get("is_anomaly", False) and r.get("anomaly_score", 0) <= th)
    raw_defects = sum(1 for r in history_records if r.get("is_anomaly", False) or r.get("anomaly_score", 0) > th)
    raw_defect_rate = (raw_defects / total_raw * 100.0) if total_raw > 0 else 0.0

    avg_score = float(np.mean(scores)) if total > 0 else 0.0
    max_score = float(np.max(scores)) if total > 0 else 0.0
    
    # Histogram buckets: <18.0, 18.0-20.0, 20.0-22.0, 22.0-23.45 (sub-threshold elevated), 23.45-26.0, >26.0
    b1 = sum(1 for s in scores if s < 18.0)
    b2 = sum(1 for s in scores if 18.0 <= s < 20.0)
    b3 = sum(1 for s in scores if 20.0 <= s < 22.0)
    b4 = sum(1 for s in scores if 22.0 <= s < th)
    b5 = sum(1 for s in scores if th <= s < 26.0)
    b6 = sum(1 for s in scores if s >= 26.0)
    
    # Chronological history trend
    chronological = list(reversed(filtered))
    trend_labels = [r.get("timestamp", f"#{i+1}") for i, r in enumerate(chronological)]
    trend_scores = [r["anomaly_score"] for r in chronological]

    return {
        "filter_applied": filter_type,
        "summary_kpis": {
            "total_inspections": total_raw,
            "filtered_inspections": total,
            "normal_count": raw_normals,
            "potential_defect_count": raw_defects,
            "potential_defect_rate_pct": round(raw_defect_rate, 2),
            "average_score": round(avg_score, 4),
            "highest_score": round(max_score, 4),
            "threshold": th
        },
        "charts": {
            "outcome_distribution": {
                "labels": ["Normal", "Potential Defect"],
                "counts": [raw_normals, raw_defects],
                "percentages": [
                    round((raw_normals / total_raw * 100), 1) if total_raw > 0 else 0.0,
                    round((raw_defects / total_raw * 100), 1) if total_raw > 0 else 0.0
                ]
            },
            "score_distribution": {
                "labels": ["<18.0", "18.0-20.0", "20.0-22.0", f"22.0-{th:.2f}", f"{th:.2f}-26.0", ">26.0"],
                "data": [b1, b2, b3, b4, b5, b6],
                "threshold": th,
                "threshold_index": 4  # Boundary between bucket 3 and 4
            },
            "defect_profile": {
                "categories": [c["name"] for c in BENCHMARK_CATEGORIES],
                "sample_counts": [c["samples"] for c in BENCHMARK_CATEGORIES],
                "detected_counts": [c["detected"] for c in BENCHMARK_CATEGORIES],
                "detection_rates": [c["detection_rate_pct"] for c in BENCHMARK_CATEGORIES],
                "mean_scores": [c["mean_score"] for c in BENCHMARK_CATEGORIES],
                "aurocs": [c["auroc"] for c in BENCHMARK_CATEGORIES],
                "threshold": th
            },
            "history_trend": {
                "labels": trend_labels,
                "scores": trend_scores,
                "threshold": th
            }
        },
        "benchmark_kpi": BENCHMARK_KPI,
        "category_benchmarks": BENCHMARK_CATEGORIES
    }
