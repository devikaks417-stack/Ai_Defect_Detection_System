"""
PROMETHEUS-X: Automotive Anomaly Detection Dashboard
Backend Application: app.py
Framework: Flask + PyTorch PatchCore (Frozen ResNet-50)
Domain: Automotive Manufacturing (AutoVI Engine Wiring)
Phase: 4.2 Advanced AI Features & Responsive Platform
"""

import os
import sys
import time
import json
import uuid
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np

from scripts import config
from scripts.predict import PatchCorePredictor
from scripts.experimental_anomaly_scoring import run_experimental_analysis
from scripts.region_analysis import analyze_defect_regions
from scripts.inspection_analytics import calculate_analytics_summary
from scripts.report_generator import generate_html_report

# Initialize Flask application
app = Flask(__name__, template_folder="templates", static_folder="static")

# Configuration
app.config["SECRET_KEY"] = "prometheus-x-automotive-inspection-key-2026"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Dedicated directories for web outputs
WEB_UPLOAD_DIR = PROJECT_ROOT / "outputs" / "web_uploads"
WEB_PRED_DIR = PROJECT_ROOT / "outputs" / "web_predictions"
WEB_EXP_DIR = PROJECT_ROOT / "outputs" / "phase4_2_experiments"
WEB_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
WEB_PRED_DIR.mkdir(parents=True, exist_ok=True)
WEB_EXP_DIR.mkdir(parents=True, exist_ok=True)

# In-memory inspection history
INSPECTION_HISTORY = []

# Global predictor instance
predictor = None

def get_predictor():
    global predictor
    if predictor is None:
        print("Initializing PatchCore predictor in Flask application...")
        predictor = PatchCorePredictor()
    return predictor

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file_path):
    """Verifies that the uploaded file is indeed a valid image."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

@app.route("/")
def index():
    """Renders the main enterprise industrial inspection dashboard."""
    eval_summary_path = config.OUTPUT_PREDICTIONS_DIR / "full_evaluation_summary.json"
    metrics = {
        "image_auroc": 0.8165,
        "pixel_auroc": 0.8724,
        "precision": 94.23,
        "recall": 15.22,
        "specificity": 98.95,
        "f1_score": 0.2620,
        "threshold": 23.4457,
        "total_test_images": 607,
        "device": config.DEVICE
    }
    if eval_summary_path.exists():
        try:
            with open(eval_summary_path, "r") as f:
                data = json.load(f)
                metrics["image_auroc"] = data.get("image_auroc", 0.8165)
                metrics["pixel_auroc"] = data.get("pixel_auroc", 0.8724)
                metrics["precision"] = round(data.get("precision", 0.9423) * 100, 2)
                metrics["recall"] = round(data.get("recall", 0.1522) * 100, 2)
                metrics["specificity"] = round(data.get("specificity", 0.9895) * 100, 2)
                metrics["f1_score"] = data.get("f1_score", 0.2620)
                metrics["threshold"] = round(data.get("calibrated_threshold", 23.4457), 4)
        except Exception as e:
            print(f"Error loading evaluation summary: {e}")

    return render_template("index.html", metrics=metrics)

@app.route("/api/inspect", methods=["POST"])
def inspect_image():
    """
    API endpoint to run PatchCore anomaly detection,
    Feature A experimental scoring, and Feature B defect region analysis.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format. Only PNG, JPG, JPEG supported."}), 400

    try:
        # Secure unique filename
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_id = str(uuid.uuid4())[:8]
        safe_name = f"{unique_id}_{secure_filename(file.filename)}"
        save_path = WEB_UPLOAD_DIR / safe_name
        file.save(save_path)

        # Validate image content
        if not validate_image_file(save_path):
            save_path.unlink(missing_ok=True)
            return jsonify({"error": "Uploaded file is corrupted or not a valid image format."}), 400

        # Run baseline inference
        pred_engine = get_predictor()
        res = pred_engine.predict(save_path)

        # File paths
        pred_filename = f"pred_{unique_id}.png"
        heatmap_filename = f"heatmap_{unique_id}.png"
        annotated_filename = f"annotated_{unique_id}.png"
        
        pred_path = WEB_PRED_DIR / pred_filename
        heatmap_path = WEB_PRED_DIR / heatmap_filename
        annotated_path = WEB_PRED_DIR / annotated_filename

        # Save standard overlay and heatmap
        import matplotlib.pyplot as plt
        plt.imsave(str(pred_path), res["overlay_np"])
        plt.imsave(str(heatmap_path), res["normalized_heatmap"], cmap="jet")

        # Feature B: Defect Region Analysis & Annotated Overlay
        reg_analysis = analyze_defect_regions(
            original_np=res["original_np"],
            heatmap=res["heatmap"],
            anomaly_score=res["anomaly_score"],
            threshold=res["threshold"],
            save_annotated_path=annotated_path
        )

        # Feature A: Experimental Inference Telemetry
        exp_analysis = run_experimental_analysis(
            heatmap=res["heatmap"],
            anomaly_score=res["anomaly_score"],
            threshold=res["threshold"]
        )

        # Result formatting
        is_anomaly = res["is_anomaly"]
        prediction_label = "Potential Defect" if is_anomaly else "Normal"

        result_data = {
            "id": unique_id,
            "filename": file.filename,
            "timestamp": time.strftime("%H:%M:%S"),
            "anomaly_score": res["anomaly_score"],
            "threshold": res["threshold"],
            "is_anomaly": is_anomaly,
            "prediction": prediction_label,
            "original_url": f"/files/uploads/{safe_name}",
            "heatmap_url": f"/files/predictions/{heatmap_filename}",
            "overlay_url": f"/files/predictions/{pred_filename}",
            "annotated_url": f"/files/predictions/{annotated_filename}",
            "report_url": f"/reports/{unique_id}",
            "region_analysis": reg_analysis,
            "experimental_analysis": exp_analysis,
            "caveat": "Research prototype. Conservative 3-sigma calibration prioritizes specificity. Sub-1% micro-defects (e.g. unclipped orange wires) may produce localized heatmaps below the global threshold."
        }

        # Add to history (capped at 50 records)
        INSPECTION_HISTORY.insert(0, result_data)
        if len(INSPECTION_HISTORY) > 50:
            INSPECTION_HISTORY.pop()

        return jsonify(result_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Inference failed: {str(e)}"}), 500

@app.route("/api/sample/<sample_type>", methods=["GET"])
def inspect_sample(sample_type):
    """API endpoint to run full inspection on a pre-packaged benchmark sample."""
    sample_map = {
        "normal": config.TEST_DIR / "good" / "0000.png",
        "cardboard": config.TEST_DIR / "cardboard" / "0000.png",
        "multiple": config.TEST_DIR / "multiple" / "0000.png",
        "fastening": config.TEST_DIR / "fastening" / "0000.png",
        "blue_hoop": config.TEST_DIR / "blue_hoop" / "0000.png",
        "obstruction": config.TEST_DIR / "obstruction" / "0000.png"
    }

    if sample_type not in sample_map:
        return jsonify({"error": f"Unknown sample type: {sample_type}"}), 400

    sample_path = sample_map[sample_type]
    if not sample_path.exists():
        return jsonify({"error": f"Sample file not found at {sample_path}"}), 404

    unique_id = f"sample_{sample_type}_{str(uuid.uuid4())[:4]}"
    safe_name = f"{unique_id}_{sample_path.name}"
    target_path = WEB_UPLOAD_DIR / safe_name
    shutil.copy(sample_path, target_path)

    try:
        pred_engine = get_predictor()
        res = pred_engine.predict(target_path)

        pred_filename = f"pred_{unique_id}.png"
        heatmap_filename = f"heatmap_{unique_id}.png"
        annotated_filename = f"annotated_{unique_id}.png"
        
        pred_path = WEB_PRED_DIR / pred_filename
        heatmap_path = WEB_PRED_DIR / heatmap_filename
        annotated_path = WEB_PRED_DIR / annotated_filename

        import matplotlib.pyplot as plt
        plt.imsave(str(pred_path), res["overlay_np"])
        plt.imsave(str(heatmap_path), res["normalized_heatmap"], cmap="jet")

        # Feature B & Feature A
        reg_analysis = analyze_defect_regions(
            original_np=res["original_np"],
            heatmap=res["heatmap"],
            anomaly_score=res["anomaly_score"],
            threshold=res["threshold"],
            save_annotated_path=annotated_path
        )
        exp_analysis = run_experimental_analysis(
            heatmap=res["heatmap"],
            anomaly_score=res["anomaly_score"],
            threshold=res["threshold"]
        )

        is_anomaly = res["is_anomaly"]
        prediction_label = "Potential Defect" if is_anomaly else "Normal"

        result_data = {
            "id": unique_id,
            "filename": f"Sample: {sample_type.replace('_', ' ').capitalize()} ({sample_path.name})",
            "timestamp": time.strftime("%H:%M:%S"),
            "anomaly_score": res["anomaly_score"],
            "threshold": res["threshold"],
            "is_anomaly": is_anomaly,
            "prediction": prediction_label,
            "original_url": f"/files/uploads/{safe_name}",
            "heatmap_url": f"/files/predictions/{heatmap_filename}",
            "overlay_url": f"/files/predictions/{pred_filename}",
            "annotated_url": f"/files/predictions/{annotated_filename}",
            "report_url": f"/reports/{unique_id}",
            "region_analysis": reg_analysis,
            "experimental_analysis": exp_analysis,
            "caveat": "Research prototype. Evaluated against official AutoVI ground truth benchmark."
        }

        INSPECTION_HISTORY.insert(0, result_data)
        if len(INSPECTION_HISTORY) > 50:
            INSPECTION_HISTORY.pop()

        return jsonify(result_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Returns aggregated inspection analytics and interactive chart data."""
    filter_type = request.args.get("filter", "all").lower()
    analytics_data = calculate_analytics_summary(INSPECTION_HISTORY, filter_type=filter_type)
    return jsonify(analytics_data)

@app.route("/api/history", methods=["GET"])
def get_history():
    """Returns the latest inspection history list."""
    return jsonify(INSPECTION_HISTORY)

@app.route("/reports/<inspection_id>")
def view_report(inspection_id):
    """Renders a standalone, printable HTML inspection report."""
    record = next((r for r in INSPECTION_HISTORY if r["id"] == inspection_id), None)
    if not record:
        return f"<h3>Inspection Report #{inspection_id} Not Found</h3><p>Session history may have been restarted.</p>", 404
        
    html_content = generate_html_report(record)
    return html_content

@app.route("/api/report/<inspection_id>/json")
def download_report_json(inspection_id):
    """Downloads raw inspection telemetry as JSON."""
    record = next((r for r in INSPECTION_HISTORY if r["id"] == inspection_id), None)
    if not record:
        return jsonify({"error": "Report not found"}), 404
    return Response(
        json.dumps(record, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=report_{inspection_id}.json"}
    )

@app.route("/files/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(WEB_UPLOAD_DIR, filename)

@app.route("/files/predictions/<path:filename>")
def serve_prediction(filename):
    return send_from_directory(WEB_PRED_DIR, filename)

if __name__ == "__main__":
    print("=" * 60)
    print("PROMETHEUS-X: Automotive Inspection Dashboard Server")
    print("Localhost URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
