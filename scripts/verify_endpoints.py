import urllib.request
import json
import sys

def run_tests():
    print("Testing PROMETHEUS-X Endpoints...")
    try:
        # 1. Main index
        res = urllib.request.urlopen("http://127.0.0.1:5000/")
        html = res.read().decode("utf-8")
        assert res.status == 200
        assert "PROMETHEUS-X" in html
        print("[PASS] GET / returned HTTP 200 with PROMETHEUS-X branding")

        # 2. Benchmarks
        samples = ["normal", "fastening", "blue_hoop", "cardboard", "multiple", "obstruction"]
        last_id = None
        for s in samples:
            res = urllib.request.urlopen(f"http://127.0.0.1:5000/api/sample/{s}")
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            score = data["anomaly_score"]
            pred = data["prediction"]
            last_id = data["id"]
            print(f"[PASS] GET /api/sample/{s} -> score={score:.2f}, pred={pred}")

        # 3. History
        res = urllib.request.urlopen("http://127.0.0.1:5000/api/history")
        assert res.status == 200
        history = json.loads(res.read().decode("utf-8"))
        print(f"[PASS] GET /api/history -> {len(history)} records")

        # 4. Analytics with filters
        res = urllib.request.urlopen("http://127.0.0.1:5000/api/analytics")
        assert res.status == 200
        analytics = json.loads(res.read().decode("utf-8"))
        print(f"[PASS] GET /api/analytics -> summary KPIs: {analytics.get('summary_kpis')}")

        res_filtered = urllib.request.urlopen("http://127.0.0.1:5000/api/analytics?filter=defect")
        assert res_filtered.status == 200
        filtered_analytics = json.loads(res_filtered.read().decode("utf-8"))
        print(f"[PASS] GET /api/analytics?filter=defect -> filtered count: {filtered_analytics['summary_kpis']['filtered_inspections']}")
        assert "defect_profile" in filtered_analytics["charts"]
        assert "score_distribution" in filtered_analytics["charts"]

        # 5. Reports
        if last_id:
            res = urllib.request.urlopen(f"http://127.0.0.1:5000/reports/{last_id}")
            assert res.status == 200
            print(f"[PASS] GET /reports/{last_id} -> HTML report generated")

            res = urllib.request.urlopen(f"http://127.0.0.1:5000/api/report/{last_id}/json")
            assert res.status == 200
            print(f"[PASS] GET /api/report/{last_id}/json -> JSON report generated")

        print("ALL FUNCTIONAL TESTS PASSED SUCCESSFULLY!")
        return 0
    except Exception as e:
        print(f"[FAIL] Error during testing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
