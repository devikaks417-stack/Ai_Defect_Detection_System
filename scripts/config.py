"""
PROMETHEUS-X: Automotive PatchCore Configuration
Module: scripts/config.py
Domain: Automotive Defect Detection (AutoVI Engine Wiring)
"""

from pathlib import Path
import torch

# Base directories
PROJECT_ROOT = Path(r"C:\Users\DEVIKA K S\Downloads\AI_Defect_Detection_System")
DATASET_ROOT = PROJECT_ROOT / "engine_wiring" / "engine_wiring"

TRAIN_GOOD_DIR = DATASET_ROOT / "train" / "good"
TEST_DIR = DATASET_ROOT / "test"
GROUND_TRUTH_DIR = DATASET_ROOT / "ground_truth"

CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints" / "automotive" / "patchcore"
OUTPUT_PREDICTIONS_DIR = PROJECT_ROOT / "outputs" / "automotive_predictions"
DOCS_DIR = PROJECT_ROOT / "docs"

# Create necessary directories
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Hardware setup
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Image Preprocessing parameters
ORIGINAL_IMAGE_SIZE = (400, 400)
INPUT_IMAGE_SIZE = (224, 224)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# PatchCore Model Parameters
BACKBONE_NAME = "resnet50"
FEATURE_LAYERS = ["layer2", "layer3"]
LAYER2_CHANNELS = 512
LAYER3_CHANNELS = 1024
PATCH_DIM = LAYER2_CHANNELS + LAYER3_CHANNELS  # 1536 dimensions

# Patch aggregation settings
PATCH_POOL_KERNEL = 3
PATCH_POOL_STRIDE = 1
PATCH_POOL_PADDING = 1

# Training & Coreset parameters
BATCH_SIZE = 16
NUM_VAL_IMAGES = 35         # Reserved normal training images for validation & threshold calibration
CORESET_SAMPLING_RATIO = 0.05  # 5% coreset subsampling ratio
PROJECTION_DIM = 128         # Johnson-Lindenstrauss random projection dimension for fast greedy minimax
RANDOM_SEED = 42

# Anomaly Scoring & Heatmap parameters
K_NEAREST_NEIGHBORS = 9
GAUSSIAN_BLUR_SIGMA = 4.0
