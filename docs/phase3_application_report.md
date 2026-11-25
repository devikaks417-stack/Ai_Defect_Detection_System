# PROMETHEUS-X: Phase 3 Localhost Web Application Report

**Project:** PROMETHEUS-X  
**Domain:** Automotive Manufacturing Visual Inspection  
**Application Type:** Research Prototype Web Dashboard  
**Architecture:** Flask + PyTorch PatchCore (Frozen ResNet-50)  
**Host Target:** Localhost (`http://127.0.0.1:5000`)  
**Report Date:** November 25, 2026  

---

## 1. System Architecture & Tech Stack

The Phase 3 web application bridges the verified PatchCore anomaly detection model with an industrial visual inspection interface.

```
AI_Defect_Detection_System/
├── app.py                      # Flask backend controller & REST API
├── templates/
│   └── index.html              # Industrial quality dashboard interface
├── static/
│   ├── css/style.css           # Modern dark-theme industrial design system
│   └── js/app.js               # Reactive upload, inference & history client
├── outputs/
│   ├── web_uploads/            # Isolated directory for temporary test uploads
│   └── web_predictions/        # Generated heatmaps & decision overlays
└── docs/
    └── phase3_application_report.md
```

### Core Technologies:
- **Backend:** Python + Flask microframework.
- **AI Engine:** PyTorch 2.6.0+cu124 with frozen ResNet-50 backbone on NVIDIA GeForce RTX 3050 GPU.
- **Frontend:** Vanilla HTML5, CSS3 (responsive grid + dark mode), and JavaScript (Fetch API, zero bulky node dependencies).

---

## 2. API Specifications & Endpoints

| Endpoint | Method | Input | Description | Output |
| :--- | :---: | :--- | :--- | :--- |
| `/` | `GET` | None | Renders main inspection dashboard with live Phase 2.5 metrics | HTML Page |
| `/api/inspect` | `POST` | Multipart Form (`file`) | Receives component image, runs inference, saves overlays | JSON result + image URLs |
| `/api/sample/<type>`| `GET` | URL param (`normal`, `blue_hoop`, `cardboard`, `fastening`, `multiple`, `obstruction`) | 1-click evaluation of benchmark images | JSON result + image URLs |
| `/api/history` | `GET` | None | Retrieves latest 30 inspections in current session | JSON history array |
| `/files/uploads/<file>` | `GET` | Filename | Serves uploaded image safely from dedicated directory | Image binary |
| `/files/predictions/<file>` | `GET` | Filename | Serves generated overlay / heatmap | Image binary |

---

## 3. Industrial Dashboard Features

1. **Model Performance Metrics Banner:** Displays the verified empirical results from Phase 2.5:
   - **Image AUROC:** `0.8165`
   - **Pixel AUROC:** `0.8724`
   - **Precision:** `94.23%` (98.95% specificity on clean engines)
   - **Recall:** `15.22%` (with warning badge explaining the 3-sigma conservative cutoff)
   - **Calibrated Threshold:** `23.4457`
2. **Dual Upload Mechanisms:**
   - **Drag-and-Drop / File Picker:** Validates file types (`.png`, `.jpg`, `.jpeg`).
   - **Quick Benchmark Testing:** Instant 1-click buttons for sample normal and defective wiring harnesses.
3. **Multi-View Visualizer:**
   - **Decision Overlay:** Original harness blended with Jet-colormap anomaly overlay.
   - **Continuous Anomaly Heatmap:** High-resolution spatial distribution of patch distances.
   - **Original Image:** Pure high-resolution camera view.
4. **Visual Score Meter:** Real-time progress bar comparing the image anomaly score against the fixed $23.45$ threshold.
5. **Inspection History Log:** Live audit trail recording timestamp, sample ID, filename, anomaly score, and outcome pill.

---

## 4. Safety, Privacy & Operational Guardrails

- **Strict Localhost Binding:** The server is configured to bind strictly to `127.0.0.1:5000` (not exposed to external networks `0.0.0.0`).
- **File Sanitization:** All incoming files are sanitized with `secure_filename` and assigned a UUID prefix to prevent collisions or directory traversal.
- **Isolated Storage:** Uploaded files are strictly stored in `outputs/web_uploads/`, completely separated from the original dataset.
- **Terminology & Compliance:** The application uses the label **"Potential Defect"** rather than claiming confirmed industrial scrap, emphasizing human-in-the-loop validation.
- **Subtle Defect Caveat:** A prominent advisory banner explains that micro-defects ($<0.8\%$ area) may yield localized heatmaps that remain below the 3-sigma factory threshold.

---

## 5. Execution Instructions

To launch the local web application:

```powershell
# 1. Activate project virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run Flask application
python app.py
```

**Localhost URL:**
👉 **`http://127.0.0.1:5000`**
