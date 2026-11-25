"""
PROMETHEUS-X: ADVANCED ANOMALY LOCALIZATION MODULE
File: scripts/experimental_anomaly_scoring.py
Domain: Automotive Manufacturing Visual Inspection

Implements isolated experimental inference methods:
1. Method A: Spatial Relative Contrast Analysis
   - Calculates local background anomaly statistics.
   - Computes peak spatial contrast elevation: Delta S = S_max - mu_bg_local.
   - Computes relative contrast ratio: R_contrast = S_max / mu_bg_local.
   - Identifies regions that are locally unusual (+25% to +40% above baseline)
     even when the absolute PatchCore score is below the global threshold.

2. Method B: Connected Patch Cluster Aggregation
   - Identifies contiguous connected components of elevated anomaly patches.
   - Computes cluster count, largest cluster area (px and %), and cluster density score.
   - Distinguishes contiguous defect structures from isolated single-patch background spikes.

IMPORTANT:
- Baseline PatchCore prediction remains 100% untouched and preserved.
- Experimental metrics are reported separately with clear research caveats.
- No test-set tuning or unvalidated thresholds are claimed as industrial standards.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import cv2

def compute_spatial_relative_contrast(
    heatmap: np.ndarray,
    anomaly_score: float,
    threshold: float = 23.4457
) -> Dict[str, Any]:
    """
    Computes spatial relative contrast metrics for a given anomaly heatmap.
    
    Args:
        heatmap: 2D numpy array (400x400) representing smoothed anomaly scores.
        anomaly_score: The global PatchCore image anomaly score (max patch score).
        threshold: The calibrated 3-sigma factory threshold (23.4457).
        
    Returns:
        dict with relative contrast metrics and diagnostic indicators.
    """
    H, W = heatmap.shape
    flat_scores = heatmap.flatten()
    
    # Estimate nominal background baseline: lower 75% of patch scores
    p75 = np.percentile(flat_scores, 75)
    bg_pixels = flat_scores[flat_scores <= p75]
    
    bg_mean = float(np.mean(bg_pixels)) if len(bg_pixels) > 0 else float(np.mean(flat_scores))
    bg_std = float(np.std(bg_pixels)) if len(bg_pixels) > 0 else float(np.std(flat_scores))
    bg_max = float(np.max(bg_pixels)) if len(bg_pixels) > 0 else float(np.max(flat_scores))
    
    peak_score = float(np.max(heatmap))
    contrast_diff = peak_score - bg_mean
    contrast_ratio = (peak_score / (bg_mean + 1e-6)) if bg_mean > 0 else 1.0
    
    # Contrast Z-score relative to local background variance
    contrast_z_score = (contrast_diff / (bg_std + 1e-6)) if bg_std > 0 else 0.0
    
    # Experimental elevation flag: local contrast > 3.0 points AND ratio >= 1.20 (+20% elevation)
    # This captures subtle fastening wires (+30% to +40% contrast) identified in Phase 4.1
    has_local_elevation = bool(contrast_diff >= 3.0 and contrast_ratio >= 1.20)
    
    return {
        "bg_estimated_mean": round(bg_mean, 4),
        "bg_estimated_std": round(bg_std, 4),
        "peak_score": round(peak_score, 4),
        "spatial_contrast_diff": round(contrast_diff, 4),
        "relative_contrast_ratio": round(contrast_ratio, 4),
        "contrast_z_score": round(contrast_z_score, 2),
        "has_local_elevation": has_local_elevation,
        "contrast_status": "Locally Elevated Contrast" if has_local_elevation else "Uniform Background",
        "caveat": "Experimental research indicator. Measures spatial contrast over estimated background. Does not override baseline decision."
    }

def compute_patch_cluster_aggregation(
    heatmap: np.ndarray,
    min_cluster_px: int = 35
) -> Dict[str, Any]:
    """
    Analyzes spatial connectivity of elevated anomaly patches.
    
    Args:
        heatmap: 2D numpy array (400x400) representing smoothed anomaly scores.
        min_cluster_px: Minimum connected pixels to qualify as a cluster (~0.02% of image).
        
    Returns:
        dict with cluster count, largest cluster area, and cluster coordinates.
    """
    H, W = heatmap.shape
    total_pixels = H * W
    
    # Adaptive threshold for anomaly cluster segmentation:
    # Points exceeding mean + 1.25 * std of the image's own distribution
    mean_val = float(np.mean(heatmap))
    std_val = float(np.std(heatmap))
    adaptive_thresh = mean_val + 1.25 * std_val
    
    binary_mask = (heatmap >= adaptive_thresh).astype(np.uint8)
    
    # Clean up small noise with morphological opening
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
    
    # Connected component labeling
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned_mask, connectivity=8)
    
    clusters = []
    total_cluster_pixels = 0
    
    # stats format: [x, y, width, height, area]
    for i in range(1, num_labels):  # Skip background (label 0)
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= min_cluster_px:
            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            w = int(stats[i, cv2.CC_STAT_WIDTH])
            h = int(stats[i, cv2.CC_STAT_HEIGHT])
            cx, cy = float(centroids[i][0]), float(centroids[i][1])
            
            # Regional score stats
            region_mask = (labels == i)
            region_scores = heatmap[region_mask]
            reg_mean = float(np.mean(region_scores))
            reg_max = float(np.max(region_scores))
            
            clusters.append({
                "id": len(clusters) + 1,
                "bbox": [x, y, w, h],
                "centroid": [round(cx, 1), round(cy, 1)],
                "pixel_area": area,
                "area_pct": round((area / total_pixels) * 100.0, 3),
                "region_mean_score": round(reg_mean, 4),
                "region_max_score": round(reg_max, 4)
            })
            total_cluster_pixels += area
            
    # Sort clusters by area descending
    clusters.sort(key=lambda c: c["pixel_area"], reverse=True)
    
    largest_cluster_area = clusters[0]["pixel_area"] if clusters else 0
    largest_cluster_pct = clusters[0]["area_pct"] if clusters else 0.0
    largest_cluster_max = clusters[0]["region_max_score"] if clusters else 0.0
    
    return {
        "cluster_count": len(clusters),
        "total_anomalous_pixels": total_cluster_pixels,
        "total_cluster_area_pct": round((total_cluster_pixels / total_pixels) * 100.0, 3),
        "largest_cluster_area_px": largest_cluster_area,
        "largest_cluster_area_pct": largest_cluster_pct,
        "largest_cluster_peak_score": round(largest_cluster_max, 4),
        "clusters": clusters[:6],  # Return up to top 6 clusters
        "has_coherent_cluster": bool(len(clusters) > 0 and largest_cluster_area >= 60),
        "caveat": "Experimental cluster analysis. Identifies spatially contiguous anomaly patterns. Research metric only."
    }

def run_experimental_analysis(
    heatmap: np.ndarray,
    anomaly_score: float,
    threshold: float = 23.4457
) -> Dict[str, Any]:
    """
    Combines Method A (Spatial Relative Contrast) and Method B (Cluster Aggregation).
    """
    contrast_res = compute_spatial_relative_contrast(heatmap, anomaly_score, threshold)
    cluster_res = compute_patch_cluster_aggregation(heatmap)
    
    return {
        "method_a_spatial_contrast": contrast_res,
        "method_b_cluster_aggregation": cluster_res,
        "is_baseline_anomaly": bool(anomaly_score > threshold),
        "baseline_threshold": threshold,
        "experimental_summary": {
            "spatial_contrast_diff": contrast_res["spatial_contrast_diff"],
            "relative_contrast_ratio": contrast_res["relative_contrast_ratio"],
            "cluster_count": cluster_res["cluster_count"],
            "largest_cluster_pct": cluster_res["largest_cluster_area_pct"],
            "status": "Potential Localized Anomaly" if (contrast_res["has_local_elevation"] or cluster_res["has_coherent_cluster"]) else "Nominal Uniform Distribution",
            "confidence_label": "Requires Operator Verification (Sub-threshold Contrast Pattern)" if (not (anomaly_score > threshold) and (contrast_res["has_local_elevation"] or cluster_res["has_coherent_cluster"])) else "Baseline Aligned"
        }
    }
