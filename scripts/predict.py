"""
PROMETHEUS-X: Automotive PatchCore Inference & Anomaly Heatmap Generation
Module: scripts/predict.py
Domain: Automotive Defect Detection (AutoVI Engine Wiring)

Provides:
- Anomaly scoring via nearest-neighbor distance to normal memory bank.
- Binary defect classification (NORMAL vs DEFECTIVE) against calibrated threshold.
- Pixel-level anomaly localization heatmap ($400x400$).
- Visual inspection overlay with alpha blending and score badge.
- CLI interface for single-image inspection and batch evaluation.
"""

import os
import sys
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms, models
from PIL import Image
import cv2
import matplotlib.pyplot as plt

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config

class PatchCorePredictor:
    def __init__(self, checkpoint_path=None, device=None):
        self.device = torch.device(device or config.DEVICE)
        checkpoint_path = Path(checkpoint_path or (config.CHECKPOINT_DIR / "patchcore_model.pt"))
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}. Train model first.")

        print(f"Loading PatchCore checkpoint from {checkpoint_path}...")
        self.checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        
        # Load memory bank into GPU memory for ultra-fast query
        self.memory_bank = self.checkpoint["memory_bank"].to(self.device)
        self.threshold = float(self.checkpoint["calibrated_threshold"])
        self.k_neighbors = int(self.checkpoint["config"].get("k_neighbors", config.K_NEAREST_NEIGHBORS))

        # Initialize frozen backbone
        weights = models.ResNet50_Weights.DEFAULT
        self.backbone = models.resnet50(weights=weights).to(self.device)
        for p in self.backbone.parameters():
            p.requires_grad = False
        self.backbone.eval()

        # Hooks
        self.features = {}
        self.backbone.layer2.register_forward_hook(self._hook("layer2"))
        self.backbone.layer3.register_forward_hook(self._hook("layer3"))

        self.pool = nn.AvgPool2d(
            kernel_size=config.PATCH_POOL_KERNEL,
            stride=config.PATCH_POOL_STRIDE,
            padding=config.PATCH_POOL_PADDING
        )

        # Transforms
        self.transform = transforms.Compose([
            transforms.Resize(config.INPUT_IMAGE_SIZE, interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.ToTensor(),
            transforms.Normalize(mean=config.IMAGENET_MEAN, std=config.IMAGENET_STD)
        ])
        print(f"Model initialized on {self.device}. Memory bank: {self.memory_bank.shape}, Threshold: {self.threshold:.4f}")

    def _hook(self, name):
        def fn(module, input, output):
            self.features[name] = output
        return fn

    def extract_patches(self, img_tensor):
        self.features.clear()
        _ = self.backbone(img_tensor)

        f2 = self.features["layer2"]
        f3 = self.features["layer3"]

        f2_pooled = self.pool(f2)
        f3_pooled = self.pool(f3)

        f3_upsampled = F.interpolate(
            f3_pooled,
            size=(f2_pooled.shape[2], f2_pooled.shape[3]),
            mode="bilinear",
            align_corners=False
        )

        patch_features = torch.cat([f2_pooled, f3_upsampled], dim=1)
        B, C, H, W = patch_features.shape
        patch_features = patch_features.permute(0, 2, 3, 1).reshape(-1, C)
        return patch_features, H, W

    def predict(self, image_path):
        """
        Runs inference on an automotive component image.
        Returns:
            dict containing:
                - image_path
                - anomaly_score
                - threshold
                - is_anomaly (bool)
                - prediction ('DEFECTIVE' / 'NORMAL')
                - heatmap (400x400 float numpy array)
                - overlay (400x400x3 uint8 RGB image)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Load original image for visualization
        orig_pil = Image.open(image_path).convert("RGB")
        orig_w, orig_h = orig_pil.size
        orig_np = np.array(orig_pil)

        # Preprocess for model
        input_tensor = self.transform(orig_pil).unsqueeze(0).to(self.device)

        with torch.no_grad():
            patches, H, W = self.extract_patches(input_tensor)
            
            # Compute distance to memory bank in chunks
            patch_dists = []
            for i in range(0, patches.shape[0], 2000):
                chunk = patches[i:i+2000]
                dist = torch.cdist(chunk, self.memory_bank)
                min_dist, _ = torch.min(dist, dim=1)
                patch_dists.append(min_dist)
            patch_dists = torch.cat(patch_dists, dim=0)

            # Image-level anomaly score is the max patch distance
            anomaly_score = float(torch.max(patch_dists).item())

            # Reshape patch distances to 2D spatial feature map
            patch_scores_2d = patch_dists.reshape(1, 1, H, W)

            # Interpolate heatmap to original image resolution (400x400)
            heatmap_tensor = F.interpolate(
                patch_scores_2d,
                size=(orig_h, orig_w),
                mode="bilinear",
                align_corners=False
            )
            raw_heatmap = heatmap_tensor.squeeze().cpu().numpy()

        # Gaussian smoothing for smooth visual heatmap
        smoothed_heatmap = cv2.GaussianBlur(raw_heatmap, (0, 0), sigmaX=config.GAUSSIAN_BLUR_SIGMA)

        # Normalize heatmap to [0, 1] relative to threshold
        norm_heatmap = np.clip((smoothed_heatmap - (self.threshold * 0.5)) / (self.threshold * 1.5), 0.0, 1.0)

        # Create colorized heatmap
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * norm_heatmap), cv2.COLORMAP_JET)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        # Alpha blend overlay
        is_anomaly = (anomaly_score > self.threshold)
        prediction_label = "DEFECTIVE" if is_anomaly else "NORMAL"
        badge_color = (255, 50, 50) if is_anomaly else (50, 200, 50)

        alpha = 0.4
        overlay = (orig_np * (1 - alpha) + heatmap_colored * alpha).astype(np.uint8)

        # Draw decision badge and scores
        overlay_pil = Image.fromarray(overlay)
        
        return {
            "image_path": str(image_path),
            "anomaly_score": round(anomaly_score, 4),
            "threshold": round(self.threshold, 4),
            "is_anomaly": bool(is_anomaly),
            "prediction": prediction_label,
            "heatmap": raw_heatmap,
            "normalized_heatmap": norm_heatmap,
            "overlay_np": overlay,
            "original_np": orig_np
        }

def save_prediction_plot(result, save_path):
    """Saves a multi-panel inspection report figure."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    
    # 1. Original image
    axes[0].imshow(result["original_np"])
    axes[0].set_title(f"Original Image\n{Path(result['image_path']).name}")
    axes[0].axis("off")

    # 2. Anomaly Heatmap
    im = axes[1].imshow(result["normalized_heatmap"], cmap="jet", vmin=0, vmax=1)
    axes[1].set_title(f"Anomaly Heatmap\nScore: {result['anomaly_score']:.4f} (Thresh: {result['threshold']:.4f})")
    axes[1].axis("off")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

    # 3. Defect Overlay
    pred_color = "red" if result["is_anomaly"] else "green"
    axes[2].imshow(result["overlay_np"])
    axes[2].set_title(f"Decision Overlay: {result['prediction']}", color=pred_color, fontweight="bold")
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved prediction visualization to {save_path}")

def main():
    parser = argparse.ArgumentParser(description="PROMETHEUS-X PatchCore Inference")
    parser.add_argument("--image", type=str, help="Path to single input image")
    parser.add_argument("--eval_samples", action="store_true", help="Run verification on sample normal and defect images")
    args = parser.parse_args()

    predictor = PatchCorePredictor()

    if args.image:
        res = predictor.predict(args.image)
        print("\n--- INFERENCE RESULT ---")
        print(f"File:       {res['image_path']}")
        print(f"Score:      {res['anomaly_score']:.4f}")
        print(f"Threshold:  {res['threshold']:.4f}")
        print(f"Prediction: {res['prediction']}")
        print("------------------------")
        
        out_file = config.OUTPUT_PREDICTIONS_DIR / f"pred_{Path(args.image).stem}.png"
        save_prediction_plot(res, out_file)

    elif args.eval_samples:
        print("\nRunning verification inference across representative sample images...")
        samples = [
            ("Normal_Test_1", config.TEST_DIR / "good" / "0000.png"),
            ("Normal_Test_2", config.TEST_DIR / "good" / "0001.png"),
            ("Defect_Fastening_1", config.TEST_DIR / "fastening" / "0000.png"),
            ("Defect_Fastening_2", config.TEST_DIR / "fastening" / "0001.png"),
            ("Defect_BlueHoop", config.TEST_DIR / "blue_hoop" / "0000.png"),
            ("Defect_Cardboard", config.TEST_DIR / "cardboard" / "0000.png"),
            ("Defect_Multiple", config.TEST_DIR / "multiple" / "0000.png")
        ]

        summary_results = []
        for label, p in samples:
            if p.exists():
                res = predictor.predict(p)
                out_file = config.OUTPUT_PREDICTIONS_DIR / f"sample_{label}.png"
                save_prediction_plot(res, out_file)
                summary_results.append({
                    "label": label,
                    "file": p.name,
                    "score": res["anomaly_score"],
                    "threshold": res["threshold"],
                    "prediction": res["prediction"],
                    "is_anomaly": res["is_anomaly"]
                })
            else:
                print(f"File not found: {p}")

        summary_path = config.OUTPUT_PREDICTIONS_DIR / "verification_inference_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary_results, f, indent=2)

        print("\n=== VERIFICATION INFERENCE SUMMARY ===")
        print(json.dumps(summary_results, indent=2))

if __name__ == "__main__":
    main()
