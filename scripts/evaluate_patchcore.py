"""
PROMETHEUS-X: Automotive PatchCore Full Model Evaluation
Module: scripts/evaluate_patchcore.py
Domain: Automotive Defect Detection (AutoVI Engine Wiring)

Evaluates:
- All 285 normal test images (test/good/)
- All 322 defective test images across 5 defect categories:
    fastening (277), multiple (33), blue_hoop (5), cardboard (5), obstruction (2)
- Total test images: 607
- Evaluates:
    - Confusion Matrix (TP, FP, TN, FN)
    - Accuracy, Precision, Recall, F1-score
    - Image-level AUROC (overall and per category)
    - Pixel-level AUROC (comparing anomaly heatmaps to ground truth masks)
    - Per-Region Overlap (PRO) score up to FPR=0.3
    - Category-by-category breakdown
    - Deep-dive investigation into fastening micro-defects
"""

import os
import sys
import time
import json
import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
import cv2
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_auc_score,
    confusion_matrix,
    precision_recall_fscore_support,
    accuracy_score,
    roc_curve
)
from scipy.ndimage import label as scipy_label

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config

def load_ground_truth_mask(category, stem):
    """Loads and combines all ground-truth masks for a given test image."""
    if category == "good":
        return np.zeros(config.ORIGINAL_IMAGE_SIZE, dtype=np.uint8)
    
    gt_dir = config.GROUND_TRUTH_DIR / category / stem
    if not gt_dir.exists():
        return np.zeros(config.ORIGINAL_IMAGE_SIZE, dtype=np.uint8)
    
    mask_files = list(gt_dir.glob("*.png"))
    combined = np.zeros(config.ORIGINAL_IMAGE_SIZE, dtype=bool)
    for mf in mask_files:
        m = cv2.imread(str(mf), cv2.IMREAD_UNCHANGED)
        if m is not None:
            if len(m.shape) == 3:
                m = m[:, :, 0]
            combined |= (m > 0)
    return (combined.astype(np.uint8) * 255)

def calculate_pro_score(all_heatmaps, all_gt_masks, max_fpr=0.3, num_thresholds=100):
    """
    Calculates the Per-Region Overlap (PRO) score.
    Measures the average overlap of each connected ground-truth defect component
    integrated up to a maximum false positive rate (default 0.3).
    """
    # Find all connected components across defective masks
    defect_components = []
    normal_pixels_total = 0
    
    for i, gt in enumerate(all_gt_masks):
        if np.any(gt > 0):
            labeled, num_features = scipy_label(gt > 0)
            for feat_idx in range(1, num_features + 1):
                defect_components.append((i, labeled == feat_idx))
        normal_pixels_total += np.count_nonzero(gt == 0)

    if len(defect_components) == 0:
        return 0.0

    # Determine threshold range
    min_val = min(float(np.min(h)) for h in all_heatmaps)
    max_val = max(float(np.max(h)) for h in all_heatmaps)
    thresholds = np.linspace(min_val, max_val, num_thresholds)

    pro_values = []
    fpr_values = []

    for th in thresholds:
        # False Positive Rate
        fp_pixels = sum(np.count_nonzero((all_heatmaps[i] >= th) & (all_gt_masks[i] == 0)) for i in range(len(all_heatmaps)))
        fpr = fp_pixels / normal_pixels_total
        fpr_values.append(fpr)

        # Average overlap per component
        overlaps = []
        for img_idx, comp_mask in defect_components:
            comp_size = np.count_nonzero(comp_mask)
            intersect = np.count_nonzero((all_heatmaps[img_idx] >= th) & comp_mask)
            overlaps.append(intersect / comp_size)
        pro_values.append(np.mean(overlaps))

    # Sort by FPR
    sorted_pairs = sorted(zip(fpr_values, pro_values), key=lambda x: x[0])
    fpr_sorted = [p[0] for p in sorted_pairs]
    pro_sorted = [p[1] for p in sorted_pairs]

    # Filter up to max_fpr
    valid_idx = [idx for idx, f in enumerate(fpr_sorted) if f <= max_fpr]
    if len(valid_idx) < 2:
        return 0.0

    sub_fpr = [fpr_sorted[i] for i in valid_idx]
    sub_pro = [pro_sorted[i] for i in valid_idx]
    
    # Area under the PRO curve divided by max_fpr
    try:
        pro_auc = float(np.trapezoid(sub_pro, sub_fpr)) / max_fpr
    except AttributeError:
        try:
            from scipy.integrate import trapezoid
            pro_auc = float(trapezoid(sub_pro, sub_fpr)) / max_fpr
        except Exception:
            pro_auc = float(np.trapz(sub_pro, sub_fpr)) / max_fpr
    return float(np.clip(pro_auc, 0.0, 1.0))

def main():
    print("=" * 60)
    print("PROMETHEUS-X: PHASE 2.5 COMPLETE MODEL EVALUATION")
    print(f"Device: {config.DEVICE}")
    print("=" * 60)

    # 1. Load Checkpoint
    checkpoint_path = config.CHECKPOINT_DIR / "patchcore_model.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")
    
    print(f"Loading verified checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    memory_bank = checkpoint["memory_bank"].to(config.DEVICE)
    calibrated_threshold = float(checkpoint["calibrated_threshold"])
    print(f"Memory Bank: {memory_bank.shape}, Calibrated Threshold: {calibrated_threshold:.4f}")

    # 2. Initialize Model Backbone
    device = torch.device(config.DEVICE)
    weights = models.ResNet50_Weights.DEFAULT
    backbone = models.resnet50(weights=weights).to(device)
    for p in backbone.parameters():
        p.requires_grad = False
    backbone.eval()

    features = {}
    def hook_l2(module, inp, out): features["layer2"] = out
    def hook_l3(module, inp, out): features["layer3"] = out
    backbone.layer2.register_forward_hook(hook_l2)
    backbone.layer3.register_forward_hook(hook_l3)

    pool = nn.AvgPool2d(
        kernel_size=config.PATCH_POOL_KERNEL,
        stride=config.PATCH_POOL_STRIDE,
        padding=config.PATCH_POOL_PADDING
    )

    transform = transforms.Compose([
        transforms.Resize(config.INPUT_IMAGE_SIZE, interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize(mean=config.IMAGENET_MEAN, std=config.IMAGENET_STD)
    ])

    # 3. Collect Test Dataset Images
    test_categories = ["good", "fastening", "multiple", "blue_hoop", "cardboard", "obstruction"]
    all_test_items = []

    for cat in test_categories:
        cat_dir = config.TEST_DIR / cat
        if cat_dir.exists():
            files = sorted(list(cat_dir.glob("*.png")))
            is_anomaly = (cat != "good")
            for f in files:
                all_test_items.append({
                    "path": f,
                    "filename": f.name,
                    "stem": f.stem,
                    "category": cat,
                    "is_anomaly": is_anomaly,
                    "true_label": 1 if is_anomaly else 0
                })

    print(f"Total test items collected: {len(all_test_items)}")
    cat_counts = {}
    for item in all_test_items:
        cat_counts[item["category"]] = cat_counts.get(item["category"], 0) + 1
    print("Test category breakdown:")
    for c, cnt in cat_counts.items():
        print(f"  {c}: {cnt}")

    # 4. Evaluate Test Images in Batches
    print("\nRunning inference over all 607 test images...")
    t_start = time.time()

    results_list = []
    pixel_heatmaps = []
    pixel_gt_masks = []

    batch_size = 16
    for i in range(0, len(all_test_items), batch_size):
        batch_items = all_test_items[i:i+batch_size]
        batch_imgs = []
        for item in batch_items:
            pil_img = Image.open(item["path"]).convert("RGB")
            batch_imgs.append(transform(pil_img))
        
        batch_tensor = torch.stack(batch_imgs, dim=0).to(device)

        with torch.no_grad():
            features.clear()
            _ = backbone(batch_tensor)

            f2_pooled = pool(features["layer2"])
            f3_pooled = pool(features["layer3"])
            f3_upsampled = F.interpolate(
                f3_pooled,
                size=(f2_pooled.shape[2], f2_pooled.shape[3]),
                mode="bilinear",
                align_corners=False
            )
            patch_feats = torch.cat([f2_pooled, f3_upsampled], dim=1)
            B, C, H, W = patch_feats.shape
            patch_feats = patch_feats.permute(0, 2, 3, 1).reshape(B, H * W, C)

            # Compute distances to memory bank for each image in batch
            for b_idx in range(B):
                item = batch_items[b_idx]
                p_img = patch_feats[b_idx]  # [784, 1536]
                
                # Chunked distance
                dists = []
                for chunk_start in range(0, p_img.shape[0], 2000):
                    p_chunk = p_img[chunk_start:chunk_start+2000]
                    cdist = torch.cdist(p_chunk, memory_bank)
                    min_dist, _ = torch.min(cdist, dim=1)
                    dists.append(min_dist)
                dists = torch.cat(dists, dim=0)

                # Anomaly score is max patch distance
                img_score = float(torch.max(dists).item())

                # Generate 2D heatmap
                heatmap_2d = dists.reshape(1, 1, H, W)
                heatmap_interp = F.interpolate(
                    heatmap_2d,
                    size=config.ORIGINAL_IMAGE_SIZE,
                    mode="bilinear",
                    align_corners=False
                ).squeeze().cpu().numpy()

                smoothed_heatmap = cv2.GaussianBlur(heatmap_interp, (0, 0), sigmaX=config.GAUSSIAN_BLUR_SIGMA)

                # Load Ground Truth mask
                gt_mask = load_ground_truth_mask(item["category"], item["stem"])

                # Store for pixel-level evaluation (subsampled by factor of 2 to preserve RAM)
                pixel_heatmaps.append(cv2.resize(smoothed_heatmap, (100, 100)))
                pixel_gt_masks.append(cv2.resize(gt_mask, (100, 100), interpolation=cv2.INTER_NEAREST))

                pred_anomaly = (img_score > calibrated_threshold)
                results_list.append({
                    "filename": item["filename"],
                    "stem": item["stem"],
                    "category": item["category"],
                    "true_label": item["true_label"],
                    "is_anomaly": item["is_anomaly"],
                    "anomaly_score": img_score,
                    "threshold": calibrated_threshold,
                    "pred_label": 1 if pred_anomaly else 0,
                    "prediction": "DEFECTIVE" if pred_anomaly else "NORMAL",
                    "correct": (item["true_label"] == (1 if pred_anomaly else 0))
                })

        if (i // batch_size + 1) % 5 == 0 or (i + batch_size) >= len(all_test_items):
            print(f"  Processed {min(i+batch_size, len(all_test_items))}/{len(all_test_items)} test images...")

    eval_time = time.time() - t_start
    print(f"Evaluation complete in {eval_time:.2f} seconds ({eval_time/len(all_test_items)*1000:.1f} ms/image).")

    # 5. Save Results CSV
    csv_path = config.OUTPUT_PREDICTIONS_DIR / "evaluation_results.csv"
    if results_list:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results_list[0].keys()))
            writer.writeheader()
            writer.writerows(results_list)
        print(f"Saved evaluation results to {csv_path}")

    # 6. Global Metric Computations
    y_true = np.array([r["true_label"] for r in results_list])
    y_pred = np.array([r["pred_label"] for r in results_list])
    y_scores = np.array([r["anomaly_score"] for r in results_list])

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    image_auroc = roc_auc_score(y_true, y_scores)

    # Pixel-level AUROC
    flat_heatmaps = np.concatenate([h.flatten() for h in pixel_heatmaps])
    flat_gt = np.concatenate([(g.flatten() > 0).astype(np.uint8) for g in pixel_gt_masks])
    pixel_auroc = roc_auc_score(flat_gt, flat_heatmaps)

    # Per-Region Overlap (PRO) score
    pro_score = calculate_pro_score(pixel_heatmaps, pixel_gt_masks, max_fpr=0.3)

    print("\n" + "=" * 50)
    print("GLOBAL EVALUATION METRICS:")
    print("=" * 50)
    print(f"Total Test Images: {len(results_list)} (Normal: {tn+fp}, Defective: {tp+fn})")
    print(f"Calibrated Threshold: {calibrated_threshold:.4f}")
    print(f"Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print(f"Accuracy:         {accuracy*100:.2f}%")
    print(f"Precision:        {precision*100:.2f}%")
    print(f"Recall:           {recall*100:.2f}%")
    print(f"F1-Score:         {f1:.4f}")
    print(f"Image-level AUROC:{image_auroc:.4f}")
    print(f"Pixel-level AUROC:{pixel_auroc:.4f}")
    print(f"PRO Score (0.3):  {pro_score:.4f}")

    # 7. Category-Specific Breakdown
    category_metrics = []
    normal_scores = np.array([r["anomaly_score"] for r in results_list if r["category"] == "good"])

    for cat in ["fastening", "multiple", "blue_hoop", "cardboard", "obstruction"]:
        cat_items = [r for r in results_list if r["category"] == cat]
        if len(cat_items) == 0:
            continue
        cat_scores = np.array([r["anomaly_score"] for r in cat_items])
        cat_y_true = np.ones(len(cat_scores))
        cat_y_pred = np.array([r["pred_label"] for r in cat_items])

        cat_tp = int(np.count_nonzero(cat_y_pred == 1))
        cat_fn = int(np.count_nonzero(cat_y_pred == 0))
        cat_recall = cat_tp / len(cat_items)

        # Category vs Normal AUROC
        pair_y_true = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(cat_scores))])
        pair_scores = np.concatenate([normal_scores, cat_scores])
        cat_auroc = roc_auc_score(pair_y_true, pair_scores)

        category_metrics.append({
            "category": cat,
            "total_samples": len(cat_items),
            "true_positive": cat_tp,
            "false_negative": cat_fn,
            "recall": round(cat_recall * 100, 2),
            "image_auroc": round(cat_auroc, 4),
            "mean_score": round(float(np.mean(cat_scores)), 4),
            "min_score": round(float(np.min(cat_scores)), 4),
            "max_score": round(float(np.max(cat_scores)), 4)
        })

    print("\nCATEGORY-SPECIFIC METRICS:")
    for cm_item in category_metrics:
        print(f"  {cm_item['category']:<12}: Samples={cm_item['total_samples']:<3} TP={cm_item['true_positive']:<3} FN={cm_item['false_negative']:<3} Recall={cm_item['recall']:>6.2f}% AUROC={cm_item['image_auroc']:.4f} MeanScore={cm_item['mean_score']:.4f}")

    # 8. Plot & Save Confusion Matrix
    cm_path = config.OUTPUT_PREDICTIONS_DIR / "confusion_matrix.png"
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f"Confusion Matrix (Threshold = {calibrated_threshold:.4f})\nAccuracy: {accuracy*100:.1f}%, F1: {f1:.3f}")
    plt.colorbar(fraction=0.046, pad=0.04)
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ["Predicted Normal", "Predicted Defect"])
    plt.yticks(tick_marks, ["Actual Normal", "Actual Defect"])
    thresh = cm.max() / 2.
    for r in range(cm.shape[0]):
        for c in range(cm.shape[1]):
            plt.text(c, r, format(cm[r, c], 'd'),
                     ha="center", va="center",
                     color="white" if cm[r, c] > thresh else "black", fontsize=14, fontweight="bold")
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(cm_path, dpi=150)
    plt.close()
    print(f"Saved confusion matrix plot to {cm_path}")

    # 9. Plot & Save Defect Category Score Distribution
    dist_path = config.OUTPUT_PREDICTIONS_DIR / "defect_category_analysis.png"
    plt.figure(figsize=(10, 6))
    cat_order = ["good", "fastening", "blue_hoop", "obstruction", "multiple", "cardboard"]
    cat_data = [[r["anomaly_score"] for r in results_list if r["category"] == c] for c in cat_order]
    
    plt.boxplot(cat_data, tick_labels=cat_order, patch_artist=True, boxprops=dict(facecolor='#8ecae6', color='#023047'))
    plt.axhline(calibrated_threshold, color="red", linestyle="--", linewidth=2, label=f"Calibrated Threshold ({calibrated_threshold:.2f})")
    plt.title("Anomaly Score Distribution Across Industrial Categories", fontsize=14, fontweight="bold")
    plt.xlabel("Category", fontsize=12)
    plt.ylabel("PatchCore Anomaly Score", fontsize=12)
    plt.legend(loc="upper left")
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(dist_path, dpi=150)
    plt.close()
    print(f"Saved category analysis plot to {dist_path}")

    # 10. Deep-Dive Fastening Investigation
    investigate_path = config.OUTPUT_PREDICTIONS_DIR / "fastening_investigation.png"
    sample_fastening_path = config.TEST_DIR / "fastening" / "0000.png"
    
    if sample_fastening_path.exists():
        sample_img = cv2.imread(str(sample_fastening_path))
        sample_rgb = cv2.cvtColor(sample_img, cv2.COLOR_BGR2RGB)
        gt_mask = load_ground_truth_mask("fastening", "0000")

        # Get heatmap
        item_res = [r for r in results_list if r["filename"] == "0000.png" and r["category"] == "fastening"][0]
        f_score = item_res["anomaly_score"]

        # Run individual prediction to extract fine heatmap
        pil_f = Image.open(sample_fastening_path).convert("RGB")
        tensor_f = transform(pil_f).unsqueeze(0).to(device)
        with torch.no_grad():
            features.clear()
            _ = backbone(tensor_f)
            f2_p = pool(features["layer2"])
            f3_p = pool(features["layer3"])
            f3_u = F.interpolate(f3_p, size=(f2_p.shape[2], f2_p.shape[3]), mode="bilinear", align_corners=False)
            pf = torch.cat([f2_p, f3_u], dim=1).permute(0, 2, 3, 1).reshape(-1, config.PATCH_DIM)
            cd = torch.cdist(pf, memory_bank)
            md, _ = torch.min(cd, dim=1)
            raw_hm = F.interpolate(md.reshape(1, 1, 28, 28), size=(400, 400), mode="bilinear", align_corners=False).squeeze().cpu().numpy()
            smooth_hm = cv2.GaussianBlur(raw_hm, (0, 0), sigmaX=3.0)

        # Calculate defect region stats vs background
        defect_pixels = smooth_hm[gt_mask > 0]
        bg_pixels = smooth_hm[gt_mask == 0]

        defect_mean = float(np.mean(defect_pixels)) if len(defect_pixels) > 0 else 0
        defect_max = float(np.max(defect_pixels)) if len(defect_pixels) > 0 else 0
        bg_mean = float(np.mean(bg_pixels))
        bg_max = float(np.max(bg_pixels))

        fig, axes = plt.subplots(1, 4, figsize=(18, 4.5))
        axes[0].imshow(sample_rgb)
        axes[0].set_title(f"Fastening Defect (0000.png)\nScore: {f_score:.2f} (Thresh: {calibrated_threshold:.2f})")
        axes[0].axis("off")

        axes[1].imshow(gt_mask, cmap="gray")
        axes[1].set_title(f"Ground Truth Defect Mask\nArea: {np.count_nonzero(gt_mask)/1600:.2f}% of image")
        axes[1].axis("off")

        im = axes[2].imshow(smooth_hm, cmap="jet")
        axes[2].set_title(f"Raw Patch Anomaly Map\nDefect Mean: {defect_mean:.2f} vs BG: {bg_mean:.2f}")
        axes[2].axis("off")
        fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)

        # Overlay with green contour
        overlay = sample_rgb.copy()
        norm_hm = np.clip((smooth_hm - bg_mean) / (defect_max - bg_mean + 1e-6), 0, 1)
        heat_col = cv2.applyColorMap(np.uint8(255 * norm_hm), cv2.COLORMAP_JET)
        heat_col = cv2.cvtColor(heat_col, cv2.COLOR_BGR2RGB)
        overlay = (sample_rgb * 0.5 + heat_col * 0.5).astype(np.uint8)
        contours, _ = cv2.findContours(gt_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
        axes[3].imshow(overlay)
        axes[3].set_title("Overlay (Green Outline = GT)")
        axes[3].axis("off")

        plt.tight_layout()
        plt.savefig(investigate_path, dpi=150)
        plt.close()
        print(f"Saved fastening investigation plot to {investigate_path}")

    # 11. Save summary JSON
    summary_eval = {
        "calibrated_threshold": calibrated_threshold,
        "total_test_images": len(results_list),
        "confusion_matrix": {"TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)},
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "image_auroc": round(float(image_auroc), 4),
        "pixel_auroc": round(float(pixel_auroc), 4),
        "pro_score": round(float(pro_score), 4),
        "category_metrics": category_metrics,
        "fastening_defect_investigation": {
            "defect_pixels_mean": round(defect_mean, 4),
            "defect_pixels_max": round(defect_max, 4),
            "bg_pixels_mean": round(bg_mean, 4),
            "bg_pixels_max": round(bg_max, 4)
        }
    }
    with open(config.OUTPUT_PREDICTIONS_DIR / "full_evaluation_summary.json", "w") as f:
        json.dump(summary_eval, f, indent=2)

    print("\nSummary evaluation JSON saved successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
