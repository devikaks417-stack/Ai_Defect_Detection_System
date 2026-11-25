# PROMETHEUS-X: Phase 4.2 Improvement Recommendations & Experiment Roadmap

**Project:** PROMETHEUS-X  
**Domain:** Automotive Manufacturing Visual Quality Inspection  
**Dataset:** AutoVI – Engine Wiring (`engine_wiring/engine_wiring/`)  
**Context:** Diagnostic findings from Phase 4.1 Error Analysis  
**Status:** Recommended Plan — Awaiting User Approval before Execution  
**Date:** November 25, 2026  

---

## 1. Executive Summary & Problem Formulation

In Phase 4.1, our quantitative analysis revealed three fundamental insights:
1. **The Model Detects the Defect Locally:** In false-negative fastening defects, the defect region exhibits a **$+4.5$ to $+6.0$ point anomaly elevation** ($+30\%$ to $+40\%$ contrast) over the background, and the spatial peak is directly centered on the unclipped wire.
2. **Receptive Field Dilution Caps Absolute Scores:** Because fastening wires are thin ($<0.8\%$ of image area), the large receptive field ($\approx 99 - 120$ px) of ResNet-50 Layer 2 + Layer 3 causes the feature vector to be composed of $\approx 95\%$ nominal background. As a result, the maximum patch score plateaus at $20.0 - 22.5$.
3. **Global Threshold Mismatch:** The conservative 3-sigma factory threshold ($23.4457$) was calibrated to suppress high-variance nominal background artifacts (which reach up to $24.11$). Consequently, subtle defect signals that fall between $20.0$ and $23.0$ are classified as `NORMAL`.

To overcome this without sacrificing factory specificity, we have formulated a prioritized roadmap of candidate improvements for Phase 4.2.

---

## 2. Ranked Experiment Roadmap for Phase 4.2

Each candidate experiment is ranked by its **Expected Diagnostic Impact**, **Implementation Complexity**, **Risk Profile**, and **Validation Prerequisites**:

| Rank | Experiment Title | Expected Usefulness | Implementation Difficulty | Risk Profile | Target Limitation Solved |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Local Relative Contrast Scoring (Spatial Baseline Normalization)** | ⭐⭐⭐⭐⭐ **High** | 🟢 **Low** (Inference-only) | 🟢 **Very Low** (No retraining required) | Eliminates absolute score dependency; leverages the $+30\%$ to $+40\%$ local contrast already proven by heatmaps. |
| **2** | **Connected-Component & Top-$K$ Patch Cluster Aggregation** | ⭐⭐⭐⭐ **High** | 🟢 **Low** (Inference-only) | 🟢 **Very Low** (No retraining required) | Replaces noisy single-patch maximum ($\max s_i$) with contiguous defect cluster density, rejecting 1-patch nominal spikes. |
| **3** | **Validation-Calibrated Threshold Optimization ($\mu + 2.0\sigma$)** | ⭐⭐⭐⭐ **High** | 🟢 **Low** (Calibration-only) | 🟡 **Low** (Increases nominal FPR from $1.0\%$ to $4.9\%$) | Directly shifts operating point on the 35 reserved nominal validation images (never using test labels). |
| **4** | **Finer Feature Granularity (Layer 1 + Layer 2 Feature Pyramid)** | ⭐⭐⭐⭐⭐ **Very High** | 🟡 **Moderate** (Requires bank retraining) | 🟡 **Low** (Requires 10–15 min memory bank regeneration) | Shrinks receptive field from $120$ px to $35$ px, drastically reducing feature dilution on thin wires. |
| **5** | **Memory Bank Coreset Density Expansion (5% $\rightarrow$ 10%)** | ⭐⭐⭐ **Moderate** | 🟡 **Moderate** (Higher RAM / GPU VRAM) | 🟡 **Moderate** (Memory bank doubles to $\approx 115$ MB) | Provides tighter normal manifold coverage around subtle wire configurations and shadows. |

---

## 3. In-Depth Experiment Specifications

### Experiment 1: Local Relative Contrast Scoring (Recommended First Step)
- **Concept:** Rather than relying exclusively on the global absolute score $S_{\text{global}} = \max_{(x,y)} S(x, y)$, compute a **Relative Contrast Score** $\Delta S$:
  $$\Delta S = \max_{(x, y)} S(x, y) - \text{Baseline}_{\text{local}}(x, y)$$
  where $\text{Baseline}_{\text{local}}$ is the regional background average or the 75th percentile of the image's non-peak pixels.
- **Why it Works:** Phase 4.1 demonstrated that fastening false negatives have $\Delta\mu = +4.5$ to $+6.0$ contrast, whereas nominal clean engines have smooth, flat spatial profiles ($\Delta\mu < 1.5$). Relative scoring decouples defect detection from global lighting/reflection variations.
- **Implementation:** Pure post-processing inference logic in `scripts/predict.py`. No retraining or model checkpoint alteration required.

### Experiment 2: Top-$K$ / Connected Patch Cluster Aggregation
- **Concept:** Replace the single-pixel maximum with a cluster-aware aggregation function:
  $$S_{\text{cluster}} = \frac{1}{|C^*|} \sum_{p \in C^*} S(p)$$
  where $C^*$ is the largest contiguous connected component of pixels exceeding a local noise floor ($S(p) > \mu_{\text{img}} + \sigma_{\text{img}}$).
- **Why it Works:** Real defects (even thin wires) activate a spatially coherent group of 20–100 adjacent patches. Spurious nominal reflections produce isolated single-patch spikes. Requiring spatial continuity filters out false alarms while boosting sensitivity to genuine defects.
- **Implementation:** Applied via morphological connected-component labeling (`cv2.connectedComponentsWithStats`) during inference.

### Experiment 3: Strict Validation Set Threshold Recalibration
- **Concept:** Using the **35 reserved nominal validation images** from Phase 2 (strictly zero test-set leakage):
  - Evaluate the empirical false-positive rate and distribution on the validation split.
  - Test calibrated thresholds at $\mu + 2.5\sigma$ ($22.98$) and $\mu + 2.0\sigma$ ($22.51$).
- **Expected Outcome:** As simulated in Phase 4.1, a shift to $\mu + 2.0\sigma$ triples fastening recall from $9.39\%$ to $27.80\%$ and boosts global recall from $15.22\%$ to $34.16\%$, while keeping test specificity at $95.09\%$ (only 14 false positives out of 285 nominal engines).
- **Implementation:** Configuration adjustment in `scripts/config.py` backed by validation set documentation.

### Experiment 4: Multi-Scale Fine-Resolution Patch Extraction
- **Concept:** Modify the PatchCore feature hook from `[Layer 2, Layer 3]` to `[Layer 1, Layer 2]`, or add Layer 1 features:
  - ResNet-50 Layer 1: stride 4, receptive field $\approx 11\times 11$ pixels.
  - ResNet-50 Layer 2: stride 8, receptive field $\approx 35\times 35$ pixels.
  - Reduce average pooling kernel from $3\times 3$ to $2\times 2$ or remove patch pooling.
- **Why it Works:** The receptive field is reduced from $120$ px down to $25 - 35$ px. A 4-pixel wire will now occupy $25\% - 40\%$ of the patch area (compared to $4\%$ previously), drastically reducing feature dilution and boosting defect distance into the high-confidence range ($>25.0$).
- **Implementation:** Requires regenerating the memory bank on the 250 normal training images (`scripts/train_patchcore.py`).

---

## 4. Risks, Constraints & Additional Data Requirements

1. **Risk of False Alarms on Factory Engines:**
   - Shifting thresholds downward or tightening feature resolution can increase false-positive rates on complex nominal wiring brackets.
   - **Mitigation:** Maintain a strict factory constraint: **Specificity must remain $\ge 95.0\%$ on nominal test images**.
2. **Computational / VRAM Constraints:**
   - Incorporating Layer 1 ($100\times 100$ spatial resolution) quadruples the number of patch vectors per image ($2,500 \rightarrow 10,000$).
   - **Mitigation:** Use random projection or targeted subsampling to fit within the RTX 3050 6 GB VRAM and system memory bounds.
3. **Data Requirements:**
   - No external datasets or new images are required. All proposed experiments operate exclusively on the approved AutoVI `engine_wiring` benchmark.
4. **Leakage Prevention Protocol:**
   - All threshold calibration and hyperparameter tuning must be performed strictly on the 35 reserved normal training images.
   - The 607 test images must remain completely unseen during optimization and used exclusively for final unbiased verification.

---

## 5. Recommended Immediate Next Step (Phase 4.2 Proposal)

**Execute Experiment 1 & Experiment 2 in a unified Non-Invasive Inference Enhancement:**
1. Keep the existing frozen model checkpoint (`patchcore_model.pt`) completely intact.
2. Implement **Spatial Relative Contrast & Patch Cluster Aggregation** in the inference pipeline.
3. Benchmark the new scoring function against the baseline to measure the gain in fastening recall and overall AUROC without altering model weights.
