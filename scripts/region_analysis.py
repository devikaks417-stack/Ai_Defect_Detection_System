"""
PROMETHEUS-X: DEFECT REGION ANALYSIS MODULE
File: scripts/region_analysis.py
Domain: Automotive Manufacturing Visual Inspection

Implements Feature B: Defect Region Analysis & Annotation
- Identifies suspicious connected regions in the anomaly heatmap.
- Computes region coordinates, bounding boxes, pixel areas, and anomaly contrast.
- Generates an annotated inspection overlay highlighting "Estimated Anomalous Regions".
- Strictly enforces non-judgmental labeling ("Potential Anomaly", "Estimated Anomalous Region",
  "Requires Manual Inspection") without asserting unvalidated defect severity.
"""

from typing import Dict, Any, List
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from scripts.experimental_anomaly_scoring import compute_patch_cluster_aggregation, compute_spatial_relative_contrast

def analyze_defect_regions(
    original_np: np.ndarray,
    heatmap: np.ndarray,
    anomaly_score: float,
    threshold: float = 23.4457,
    save_annotated_path: Path = None
) -> Dict[str, Any]:
    """
    Performs regional defect analysis and optionally generates an annotated visual overlay.
    
    Args:
        original_np: (400, 400, 3) uint8 RGB numpy array.
        heatmap: (400, 400) float numpy array.
        anomaly_score: Global PatchCore anomaly score.
        threshold: Decision threshold.
        save_annotated_path: File path to save annotated overlay image.
        
    Returns:
        dict containing regional metrics, bounding boxes, and annotation details.
    """
    H, W, _ = original_np.shape
    total_pixels = H * W
    
    # 1. Cluster and contrast metrics
    cluster_data = compute_patch_cluster_aggregation(heatmap)
    contrast_data = compute_spatial_relative_contrast(heatmap, anomaly_score, threshold)
    
    clusters = cluster_data["clusters"]
    num_regions = len(clusters)
    
    # Region analysis metrics
    highest_score = round(float(np.max(heatmap)), 4)
    mean_score = round(float(np.mean(heatmap)), 4)
    total_area_pct = cluster_data["total_cluster_area_pct"]
    largest_region_px = cluster_data["largest_cluster_area_px"]
    largest_region_pct = cluster_data["largest_cluster_area_pct"]
    
    # Build detailed region list
    region_details = []
    for idx, c in enumerate(clusters):
        x, y, w, h = c["bbox"]
        cx, cy = c["centroid"]
        
        region_details.append({
            "region_id": idx + 1,
            "label": f"Estimated Anomalous Region #{idx + 1}",
            "bounding_box": {"x": x, "y": y, "width": w, "height": h},
            "centroid": {"x": cx, "y": cy},
            "pixel_area": c["pixel_area"],
            "area_percentage": c["area_pct"],
            "region_mean_score": c["region_mean_score"],
            "region_peak_score": c["region_max_score"],
            "relative_contrast": round(c["region_max_score"] - contrast_data["bg_estimated_mean"], 4),
            "status_flag": "Requires Manual Inspection",
            "morphology": "Compact Cluster" if (w/max(h,1) >= 0.5 and w/max(h,1) <= 2.0) else "Linear / Wire Pattern"
        })

    # 2. Generate annotated overlay image
    # Blend original image with colorized heatmap (Jet)
    norm_heatmap = np.clip((heatmap - (threshold * 0.5)) / (threshold * 1.5), 0.0, 1.0)
    heatmap_colored = cv2.applyColorMap(np.uint8(255 * norm_heatmap), cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
    
    alpha = 0.35
    annotated = (original_np * (1 - alpha) + heatmap_colored * alpha).astype(np.uint8)
    
    # Draw bounding boxes and region tags on annotated image
    # Use OpenCV for crisp drawing
    for r in region_details:
        bb = r["bounding_box"]
        x, y, w, h = bb["x"], bb["y"], bb["width"], bb["height"]
        
        # Color: Cyan (#00E5FF in BGR: 255, 229, 0) for high visibility
        color = (0, 229, 255)
        # Bounding box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        
        # Tag badge
        badge_text = f"Region #{r['region_id']} ({r['area_percentage']}%, Max: {r['region_peak_score']})"
        font_scale = 0.38
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        
        # Draw background pill for text
        tag_y1 = max(0, y - th - 6)
        tag_y2 = y
        cv2.rectangle(annotated, (x, tag_y1), (x + tw + 6, tag_y2), (20, 24, 33), -1)
        cv2.rectangle(annotated, (x, tag_y1), (x + tw + 6, tag_y2), color, 1)
        cv2.putText(annotated, badge_text, (x + 3, tag_y2 - 3), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)

    # Save annotated overlay if path provided
    if save_annotated_path:
        save_annotated_path = Path(save_annotated_path)
        save_annotated_path.parent.mkdir(parents=True, exist_ok=True)
        # Convert RGB to BGR for OpenCV imwrite
        cv2.imwrite(str(save_annotated_path), cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))

    return {
        "highest_anomaly_score": highest_score,
        "mean_anomaly_score": mean_score,
        "num_suspicious_regions": num_regions,
        "total_suspicious_area_pct": total_area_pct,
        "largest_region_area_px": largest_region_px,
        "largest_region_area_pct": largest_region_pct,
        "local_background_mean": contrast_data["bg_estimated_mean"],
        "spatial_contrast_diff": contrast_data["spatial_contrast_diff"],
        "regions": region_details,
        "inspection_recommendation": "Potential Anomaly Detected — Requires Manual Inspection" if (num_regions > 0 or anomaly_score > threshold) else "Nominal Component — No Significant Anomalies Observed",
        "caveat": "Estimated anomalous regions are derived from local spatial contrast. Does not assert confirmed manufacturing defect severity."
    }
