# PROMETHEUS-X: Automotive PatchCore Model Training Report

**Project:** PROMETHEUS-X  
**Domain:** Automotive Manufacturing Visual Inspection  
**Dataset:** AutoVI – `engine_wiring`  
**Execution Date:** November 25, 2026  
**Training Hardware:** NVIDIA GeForce RTX 3050 Laptop GPU (6 GB VRAM)  
**Execution Environment:** Isolated `.venv` (Python 3.11, PyTorch 2.6.0+cu124)  

---

## 1. Dataset Partitioning & Anti-Leakage Compliance

The AutoVI engine wiring dataset contains 285 nominal images in `train/good/`. In strict accordance with the non-leakage rules:
- **Zero defective images were used during training or threshold calibration.**
- The 285 normal training images were partitioned deterministically (`seed=42`) into:
  - **Memory Bank Construction Set:** **250 images** (`train/good/`)
  - **Validation Calibration Set:** **35 images** (`train/good/`)
- All 607 test images (`test/good/` and defect categories) remained completely untouched during training.

---

## 2. Hardware Resource Utilization & Timing

| Phase | Metric / Measurement | Observation |
| :--- | :--- | :--- |
| **Backbone VRAM Footprint** | 108.79 MB Allocated / 142.0 MB Reserved | Frozen ResNet-50 occupies <2% of 6GB VRAM |
| **Feature Extraction Time** | **5.26 seconds** (250 images, batch size 16) | ~21 ms per image throughput on CUDA |
| **Raw Patch Tensor Size** | $196,000 \times 1536$ float32 = **1,148.44 MB** | Streamed safely to CPU memory |
| **Coreset Selection Time** | **58.19 seconds** | Random-projection guided greedy minimax |
| **Final Memory Bank Size** | $9,800 \times 1536$ float32 = **57.42 MB** | 95% storage reduction vs raw features |
| **Total Pipeline Runtime** | **68.7 seconds** | Zero GPU OOM or system RAM pressure |

---

## 3. Threshold Calibration on Reserved Normal Validation Images

To establish an objective binary decision boundary without peeking at defective test data, the 35 reserved normal validation images were evaluated against the constructed memory bank:

| Metric | Score | Industrial Interpretation |
| :--- | :---: | :--- |
| **Nominal Mean ($\mu$)** | **20.6538** | Baseline nominal distance to nearest memory bank patches |
| **Nominal Std Dev ($\sigma$)** | **0.9306** | Tight variance indicating consistent feature representation |
| **Nominal Min Score** | 19.1245 | Minimum observed nominal patch distance |
| **Nominal 95th Percentile** | 22.2151 | 95% of normal images fall below this value |
| **Nominal 99th Percentile** | 22.7556 | 99% of normal images fall below this value |
| **Nominal Max Score** | 22.9639 | Maximum observed normal variation in validation split |
| **Calibrated Threshold ($\mu + 3\sigma$)** | **23.4457** | Conservative 3-sigma decision boundary (99.7% nominal specificity) |

---

## 4. Key Takeaways & Training Validation

1. **Non-Gradient Convergence:** Unlike standard deep learning models that require iterative optimization epochs and loss curve tracking, PatchCore constructs its representational space in a single pass.
2. **Low Memory Footprint:** The final model artifact requires only **57.42 MB**, making it lightweight and suitable for edge deployment.
3. **Reproducibility:** Seeded with `RANDOM_SEED = 42` for exact reproducibility of the projection matrix and train/val split.
