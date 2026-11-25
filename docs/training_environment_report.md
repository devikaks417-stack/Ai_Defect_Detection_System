# PROMETHEUS-X: Training Environment & Hardware Inspection Report

**Generated Date:** November 25, 2026  
**Project:** PROMETHEUS-X (Automotive Defect Detection)  
**Target Architecture:** PatchCore Anomaly Detection  

---

## 1. System Hardware Specifications

| Component | Specification | Operational Status |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Home / Pro (Build 10.0.26300, 64-bit) | ✅ Healthy |
| **Processor (CPU)** | Intel Core (13th/14th Gen, Model 183) — 16 Logical Cores | ✅ High Performance |
| **System RAM** | 15.69 GB Total (~16 GB) / **2.17 GB Available** | ⚠️ Limited Headroom (Requires coreset subsampling) |
| **Dedicated GPU** | NVIDIA GeForce RTX 3050 Laptop GPU (6144 MiB / 6 GB VRAM) | ✅ Active (0 MiB used, 6 GB free) |
| **NVIDIA Driver** | 610.60 | ✅ Fully Updated |
| **CUDA Capability** | CUDA 12.x / 13.x Supported (UMD 13.3) | ✅ Ready for GPU Acceleration |
| **Disk Storage (C:)** | 300.96 GB Total / **65.12 GB Free** | ✅ Sufficient for dependencies & checkpoints |

---

## 2. Python Environment & Existing Packages

- **Python Version:** `3.11.0` (64-bit)
- **Interpreter Path:** `C:\Users\DEVIKA K S\AppData\Local\Programs\Python\Python311\python.exe`
- **Virtual Environment Active:** `No` (System Python 3.11)

### Installed Key Libraries:
- **Computer Vision & Imaging:** `pillow` (10.3.0), `opencv-python-headless` (4.10.0.84)
- **Scientific Computing & ML:** `numpy` (1.26.4), `scipy` (1.17.1), `scikit-learn` (1.5.1), `pandas` (2.2.2), `matplotlib` (3.11.2)
- **Deep Learning Frameworks Present:** `tensorflow` (2.21.0), `keras` (3.15.1)
- **Missing Core Frameworks:**
  - ❌ `torch` (PyTorch) is **NOT installed**
  - ❌ `torchvision` is **NOT installed**

---

## 3. Dependency Gap Analysis for PatchCore

PatchCore relies on a deep convolutional vision backbone (typically **WideResNet-50-2** or **ResNet-50**) to extract mid-level hierarchical feature maps (Layers 2 & 3), followed by adaptive average pooling, neighborhood patch aggregation, greedy coreset subsampling, and nearest-neighbor distance scoring.

While `scikit-learn` and `opencv` are already installed, PyTorch and torchvision are required for feature extraction using the pretrained backbone weights.

### Recommended Packages to Install:

| Package | Recommended Version | Justification |
| :--- | :--- | :--- |
| **`torch`** | `2.5.1+cu124` or `2.5.1` (CPU) | Modern stable PyTorch build with native CUDA 12.4 support matching the RTX 3050 and Python 3.11. |
| **`torchvision`** | `0.20.1+cu124` or `0.20.1` (CPU) | Contains official standard torchvision backbones (`wide_resnet50_2`, `resnet50`). |

> [!IMPORTANT]
> **GPU vs CPU Recommendation:**
> Because the machine possesses an **NVIDIA GeForce RTX 3050 Laptop GPU** with **6 GB of free VRAM**, installing PyTorch with CUDA support (`--index-url https://download.pytorch.org/whl/cu124`) will allow:
> 1. Fast, hardware-accelerated patch feature extraction (under 30 seconds for 285 images).
> 2. Offloading memory from system RAM (which has only 2.17 GB free) directly into the GPU's dedicated 6 GB VRAM.
> Alternatively, a CPU-only PyTorch build can be installed if a smaller download footprint is preferred.

---

## 4. Next Step & Action Required

In accordance with Phase 2 strict rules (*"If dependencies are missing, recommend compatible versions and ask for approval before installation"*), **no packages have been installed.**

Awaiting user approval to install `torch` and `torchvision`.
