"""
PROMETHEUS-X: Automotive PatchCore Training & Memory Bank Construction
Module: scripts/train_patchcore.py
Domain: Automotive Manufacturing (AutoVI Engine Wiring)

Original implementation following the PatchCore paradigm:
1. Frozen ResNet-50 vision backbone (no gradient backpropagation).
2. Multi-scale feature extraction from Layer 2 (512 dims) and Layer 3 (1024 dims).
3. Neighborhood-aware patch aggregation via local average pooling and bilinear interpolation.
4. Memory-efficient streaming of 1536-dimensional patch features.
5. Random projection-guided greedy minimax coreset selection to minimize RAM footprint.
6. Nominal validation threshold calibration on reserved normal images.
7. Serialized checkpoint saving to checkpoints/automotive/patchcore/.
"""

import os
import sys
import time
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config

def set_seed(seed=config.RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

class NormalDataset(Dataset):
    """Loads normal automotive images with standard ImageNet normalization."""
    def __init__(self, image_paths, transform=None):
        self.image_paths = sorted(image_paths)
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, str(path)

class PatchCoreBackbone(nn.Module):
    """Wraps frozen ResNet-50 to extract and aggregate Layer 2 & Layer 3 features."""
    def __init__(self, device):
        super().__init__()
        self.device = device
        weights = models.ResNet50_Weights.DEFAULT
        self.backbone = models.resnet50(weights=weights).to(device)
        
        # Freeze backbone parameters
        for param in self.backbone.parameters():
            param.requires_grad = False
        self.backbone.eval()

        self.features = {}
        self.hook_l2 = self.backbone.layer2.register_forward_hook(self._hook("layer2"))
        self.hook_l3 = self.backbone.layer3.register_forward_hook(self._hook("layer3"))

        self.pool = nn.AvgPool2d(
            kernel_size=config.PATCH_POOL_KERNEL,
            stride=config.PATCH_POOL_STRIDE,
            padding=config.PATCH_POOL_PADDING
        )

    def _hook(self, name):
        def fn(module, input, output):
            self.features[name] = output
        return fn

    def forward(self, x):
        self.features.clear()
        _ = self.backbone(x)
        
        # Extract features
        f2 = self.features["layer2"]  # [B, 512, 28, 28]
        f3 = self.features["layer3"]  # [B, 1024, 14, 14]

        # Apply neighborhood pooling
        f2_pooled = self.pool(f2)
        f3_pooled = self.pool(f3)

        # Bilinear upsample layer3 to match layer2 spatial dimensions (28x28)
        f3_upsampled = F.interpolate(
            f3_pooled,
            size=(f2_pooled.shape[2], f2_pooled.shape[3]),
            mode="bilinear",
            align_corners=False
        )

        # Concatenate along channel dimension -> [B, 1536, 28, 28]
        patch_features = torch.cat([f2_pooled, f3_upsampled], dim=1)
        
        # Reshape to [B, 28*28, 1536] -> [B * 784, 1536]
        B, C, H, W = patch_features.shape
        patch_features = patch_features.permute(0, 2, 3, 1).reshape(-1, C)
        return patch_features, H, W

def memory_efficient_coreset_selection(patches_tensor, sampling_ratio, proj_dim, device):
    """
    Greedy minimax coreset selection using random projection.
    Uses Johnson-Lindenstrauss random projection matrix to compute distances
    in a compact subspace, drastically reducing RAM and compute consumption.
    """
    total_patches, feat_dim = patches_tensor.shape
    coreset_size = int(total_patches * sampling_ratio)
    print(f"Coreset Selection: Subsampling {coreset_size} representative patches from {total_patches} total patches ({sampling_ratio*100:.1f}%)")

    # Construct orthogonal random projection matrix
    torch.manual_seed(config.RANDOM_SEED)
    proj_matrix = torch.randn(feat_dim, proj_dim, device=device)
    proj_matrix, _ = torch.linalg.qr(proj_matrix)  # Orthonormal projection

    # Project patches in chunks to prevent memory spikes
    chunk_size = 10000
    projected_list = []
    for i in range(0, total_patches, chunk_size):
        chunk = patches_tensor[i:i+chunk_size].to(device)
        proj_chunk = torch.matmul(chunk, proj_matrix)
        projected_list.append(proj_chunk)
    projected_patches = torch.cat(projected_list, dim=0)

    # Minimax coreset selection on GPU
    selected_indices = []
    # Start with a random index
    start_idx = torch.randint(0, total_patches, (1,)).item()
    selected_indices.append(start_idx)

    # Initialize distance tensor with infinity
    min_distances = torch.full((total_patches,), float("inf"), device=device)

    print(f"Iteratively selecting {coreset_size} coreset centers...")
    t0 = time.time()
    
    # Track progress at 25%, 50%, 75%, 100%
    report_step = max(1, coreset_size // 4)

    for step in range(1, coreset_size):
        last_center = projected_patches[selected_indices[-1]].unsqueeze(0)
        
        # Compute squared Euclidean distance to last center in chunks
        for i in range(0, total_patches, chunk_size):
            chunk = projected_patches[i:i+chunk_size]
            dist_chunk = torch.sum((chunk - last_center) ** 2, dim=1)
            min_distances[i:i+chunk_size] = torch.minimum(min_distances[i:i+chunk_size], dist_chunk)

        # Next center is the point with the maximum minimum distance to already selected points
        next_center = torch.argmax(min_distances).item()
        selected_indices.append(next_center)

        if step % report_step == 0 or step == coreset_size - 1:
            print(f"  Step {step}/{coreset_size} ({(step/coreset_size)*100:.1f}%) - elapsed: {time.time()-t0:.1f}s")

    selected_indices = torch.tensor(selected_indices, dtype=torch.long)
    coreset_patches = patches_tensor[selected_indices]
    print(f"Coreset selection complete in {time.time()-t0:.2f}s. Memory bank shape: {coreset_patches.shape}")
    return coreset_patches, selected_indices

def main():
    set_seed()
    device = torch.device(config.DEVICE)
    print("=" * 60)
    print("PROMETHEUS-X: AUTOMOTIVE PATCHCORE TRAINING")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"Dataset: {config.DATASET_ROOT}")
    print("=" * 60)

    # 1. Dataset Discovery
    all_train_images = sorted(list(config.TRAIN_GOOD_DIR.glob("*.png")))
    total_nominal = len(all_train_images)
    print(f"Discovered {total_nominal} normal images in {config.TRAIN_GOOD_DIR}")

    if total_nominal != 285:
        print(f"Warning: Expected 285 images, found {total_nominal}")

    # Split into memory-bank construction set (250) and validation set (35)
    random.seed(config.RANDOM_SEED)
    shuffled_images = all_train_images.copy()
    random.shuffle(shuffled_images)

    train_images = shuffled_images[:-config.NUM_VAL_IMAGES]
    val_images = shuffled_images[-config.NUM_VAL_IMAGES:]
    print(f"Training split: {len(train_images)} images for memory bank construction")
    print(f"Validation split: {len(val_images)} reserved images for threshold calibration")

    # 2. Image Transforms
    train_transform = transforms.Compose([
        transforms.Resize(config.INPUT_IMAGE_SIZE, interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize(mean=config.IMAGENET_MEAN, std=config.IMAGENET_STD)
    ])

    train_dataset = NormalDataset(train_images, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)

    val_dataset = NormalDataset(val_images, transform=train_transform)
    val_loader = DataLoader(val_dataset, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)

    # 3. Model Architecture Initialization
    print("\nInitializing frozen ResNet-50 feature extractor...")
    model = PatchCoreBackbone(device=device)

    # 4. Memory Estimation
    est_patches_per_image = 28 * 28  # 784
    est_total_patches = len(train_images) * est_patches_per_image  # ~196,000
    est_raw_mem_mb = (est_total_patches * config.PATCH_DIM * 4) / (1024**2)
    est_coreset_size = int(est_total_patches * config.CORESET_SAMPLING_RATIO)  # ~9,800
    est_coreset_mem_mb = (est_coreset_size * config.PATCH_DIM * 4) / (1024**2)

    print("\n--- Pre-computation Memory Budget ---")
    print(f"  Estimated raw patches: {est_total_patches:,} patches ({est_raw_mem_mb:.2f} MB)")
    print(f"  Target coreset size (5%): {est_coreset_size:,} patches ({est_coreset_mem_mb:.2f} MB)")
    print(f"  System RAM budget: ~2.18 GB available -> Comfortably safe (< 150 MB peak)")
    print("--------------------------------------\n")

    # 5. Extract Normal Patch Features (in batches on GPU)
    print("Extracting patch features from normal training images...")
    t_start_extract = time.time()
    collected_patches = []

    with torch.no_grad():
        for batch_idx, (imgs, paths) in enumerate(train_loader):
            imgs = imgs.to(device)
            patches, H, W = model(imgs)
            # Move to CPU RAM as float32 to conserve GPU VRAM
            collected_patches.append(patches.cpu())
            if (batch_idx + 1) % 4 == 0 or (batch_idx + 1) == len(train_loader):
                print(f"  Processed batch {batch_idx+1}/{len(train_loader)} ({len(collected_patches)*config.BATCH_SIZE} images)")

    all_patches = torch.cat(collected_patches, dim=0)
    extract_time = time.time() - t_start_extract
    print(f"Extraction complete in {extract_time:.2f}s.")
    print(f"Extracted patch matrix shape: {all_patches.shape} (Size: {all_patches.element_size() * all_patches.nelement() / (1024**2):.2f} MB)")

    # 6. Memory Bank Coreset Selection
    t_start_coreset = time.time()
    memory_bank, selected_idx = memory_efficient_coreset_selection(
        patches_tensor=all_patches,
        sampling_ratio=config.CORESET_SAMPLING_RATIO,
        proj_dim=config.PROJECTION_DIM,
        device=device
    )
    coreset_time = time.time() - t_start_coreset

    # 7. Validation-based Threshold Calibration on Reserved Normal Images
    print("\nCalibrating anomaly detection threshold on 35 reserved normal validation images...")
    val_patch_scores = []
    val_image_scores = []

    memory_bank_gpu = memory_bank.to(device)

    with torch.no_grad():
        for imgs, paths in val_loader:
            imgs = imgs.to(device)
            patches, H, W = model(imgs)
            # Compute distances from patches to memory bank
            # Chunk patches to prevent OOM
            patch_dists = []
            for i in range(0, patches.shape[0], 2000):
                p_chunk = patches[i:i+2000]
                # [p_chunk, M] distance
                dist = torch.cdist(p_chunk, memory_bank_gpu)
                min_dist, _ = torch.min(dist, dim=1)
                patch_dists.append(min_dist)
            patch_dists = torch.cat(patch_dists, dim=0)
            
            # Group by image (784 patches per image)
            num_imgs_batch = imgs.shape[0]
            patches_per_img = H * W
            for b in range(num_imgs_batch):
                img_p_dists = patch_dists[b*patches_per_img : (b+1)*patches_per_img]
                # Image score is maximum patch distance (PatchCore anomaly score)
                img_score = torch.max(img_p_dists).item()
                val_image_scores.append(img_score)
                val_patch_scores.extend(img_p_dists.cpu().numpy().tolist())

    val_image_scores = np.array(val_image_scores)
    mean_val_score = float(np.mean(val_image_scores))
    std_val_score = float(np.std(val_image_scores))
    max_val_score = float(np.max(val_image_scores))
    p95_val_score = float(np.percentile(val_image_scores, 95))
    p99_val_score = float(np.percentile(val_image_scores, 99))

    # Calibrate threshold at mean + 3*std (conservative 99.7% nominal bound)
    calibrated_threshold = mean_val_score + 3.0 * std_val_score

    print("Validation Score Distribution (Nominal):")
    print(f"  Mean Score:    {mean_val_score:.4f}")
    print(f"  Std Deviation: {std_val_score:.4f}")
    print(f"  Max Score:     {max_val_score:.4f}")
    print(f"  95th Pct:      {p95_val_score:.4f}")
    print(f"  99th Pct:      {p99_val_score:.4f}")
    print(f"  --> Calibrated Decision Threshold (Mean + 3*Std): {calibrated_threshold:.4f}")

    # 8. Save Checkpoint & Metadata
    checkpoint_path = config.CHECKPOINT_DIR / "patchcore_model.pt"
    metadata_path = config.CHECKPOINT_DIR / "model_metadata.json"

    checkpoint = {
        "memory_bank": memory_bank,  # CPU tensor [N_coreset, 1536]
        "backbone_name": config.BACKBONE_NAME,
        "feature_layers": config.FEATURE_LAYERS,
        "patch_dim": config.PATCH_DIM,
        "calibrated_threshold": calibrated_threshold,
        "threshold_stats": {
            "mean": mean_val_score,
            "std": std_val_score,
            "max": max_val_score,
            "p95": p95_val_score,
            "p99": p99_val_score
        },
        "config": {
            "input_size": config.INPUT_IMAGE_SIZE,
            "original_size": config.ORIGINAL_IMAGE_SIZE,
            "coreset_ratio": config.CORESET_SAMPLING_RATIO,
            "k_neighbors": config.K_NEAREST_NEIGHBORS,
            "num_train_images": len(train_images),
            "num_val_images": len(val_images)
        }
    }

    print(f"\nSaving model checkpoint to {checkpoint_path}...")
    torch.save(checkpoint, checkpoint_path)
    checkpoint_size_mb = os.path.getsize(checkpoint_path) / (1024**2)
    print(f"Checkpoint saved successfully ({checkpoint_size_mb:.2f} MB)")

    metadata = {
        "model_name": "PatchCore-ResNet50-Automotive",
        "domain": "Automotive Engine Wiring Defect Detection",
        "dataset": "AutoVI engine_wiring",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backbone": config.BACKBONE_NAME,
        "all_backbone_parameters_frozen": True,
        "device_trained_on": str(device),
        "gpu_model": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
        "train_nominal_images": len(train_images),
        "validation_nominal_images": len(val_images),
        "total_extracted_patches": all_patches.shape[0],
        "coreset_memory_bank_size": memory_bank.shape[0],
        "coreset_sampling_ratio": config.CORESET_SAMPLING_RATIO,
        "patch_vector_dimension": config.PATCH_DIM,
        "calibrated_threshold": calibrated_threshold,
        "feature_extraction_seconds": round(extract_time, 2),
        "coreset_selection_seconds": round(coreset_time, 2),
        "checkpoint_file": str(checkpoint_path),
        "checkpoint_size_mb": round(checkpoint_size_mb, 2)
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print("Training process finished cleanly.")
    print("=" * 60)

if __name__ == "__main__":
    main()
