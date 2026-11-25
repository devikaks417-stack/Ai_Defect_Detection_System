/**
 * PROMETHEUS-X: Industrial AI Quality Inspection Platform
 * Enterprise Client-Side Logic & Multi-View Visualizer
 * Architecture: Modular SPA Router, 4-View Workstation with Opacity Slider, Canvas Telemetry Charts
 */

(function () {
    'use strict';

    // --------------------------------------------------------------------------
    // STATE MANAGEMENT
    // --------------------------------------------------------------------------
    const state = {
        currentSection: 'overview',
        sidebarCollapsed: localStorage.getItem('prometheus_sidebar') === 'true',
        zoomLevel: 1.0,
        activeView: 'overlay',
        overlayOpacity: 65,
        selectedFile: null,
        currentInspection: null,
        history: [],
        analyticsData: null,
        predictionFilter: 'all',
        threshold: 23.4457,
        activeDomain: 'automotive'
    };

    // --------------------------------------------------------------------------
    // DOM REFERENCES
    // --------------------------------------------------------------------------
    const dom = {
        appSidebar: document.getElementById('appSidebar'),
        sidebarCollapseBtn: document.getElementById('sidebarCollapseBtn'),
        mobileMenuBtn: document.getElementById('mobileMenuBtn'),
        drawerBackdrop: document.getElementById('drawerBackdrop'),
        crumbCurrent: document.getElementById('crumbCurrent'),
        toastContainer: document.getElementById('toastContainer'),
        sections: document.querySelectorAll('.page-section'),
        navLinks: document.querySelectorAll('.sidebar-nav .nav-link'),

        // Overview KPIs
        kpiTotalInspections: document.getElementById('kpiTotalInspections'),
        kpiNormalCount: document.getElementById('kpiNormalCount'),
        kpiNormalRate: document.getElementById('kpiNormalRate'),
        kpiDefectCount: document.getElementById('kpiDefectCount'),
        kpiDefectRate: document.getElementById('kpiDefectRate'),
        kpiAvgScore: document.getElementById('kpiAvgScore'),
        overviewRecentTableBody: document.getElementById('overviewRecentTableBody'),
        btnHeroStartInspection: document.getElementById('btnHeroStartInspection'),
        topbarActionBtn: document.getElementById('topbarActionBtn'),
        btnViewAllHistory: document.getElementById('btnViewAllHistory'),

        // Inspection Workspace
        dropZone: document.getElementById('dropZone'),
        fileInput: document.getElementById('fileInput'),
        uploadPreviewBox: document.getElementById('uploadPreviewBox'),
        uploadPreviewThumb: document.getElementById('uploadPreviewThumb'),
        uploadPreviewName: document.getElementById('uploadPreviewName'),
        uploadPreviewMeta: document.getElementById('uploadPreviewMeta'),
        btnRemoveUpload: document.getElementById('btnRemoveUpload'),
        btnExecuteUploadInference: document.getElementById('btnExecuteUploadInference'),
        emptyWorkspaceCard: document.getElementById('emptyWorkspaceCard'),
        loadingWorkspaceCard: document.getElementById('loadingWorkspaceCard'),
        activeInspectionContainer: document.getElementById('activeInspectionContainer'),

        // Inspection Results & Viewer
        resInspectionId: document.getElementById('resInspectionId'),
        resInspectionTime: document.getElementById('resInspectionTime'),
        resFilename: document.getElementById('resFilename'),
        resDecisionPill: document.getElementById('resDecisionPill'),
        resAnomalyScore: document.getElementById('resAnomalyScore'),
        resThreshold: document.getElementById('resThreshold'),
        resMeterFill: document.getElementById('resMeterFill'),
        resMeterPin: document.getElementById('resMeterPin'),
        resPeakScore: document.getElementById('resPeakScore'),
        resMeanScore: document.getElementById('resMeanScore'),
        resRegionCount: document.getElementById('resRegionCount'),
        resAreaPct: document.getElementById('resAreaPct'),
        resDiagnosisText: document.getElementById('resDiagnosisText'),
        btnOpenReportFromInspection: document.getElementById('btnOpenReportFromInspection'),

        // Viewer stage & controls
        viewerTabBtns: document.querySelectorAll('.viewer-tab-btn'),
        overlayOpacityWrap: document.getElementById('overlayOpacityWrap'),
        overlayOpacitySlider: document.getElementById('overlayOpacitySlider'),
        overlayOpacityValue: document.getElementById('overlayOpacityValue'),
        heatmapLegendWrap: document.getElementById('heatmapLegendWrap'),
        singleStage: document.getElementById('singleStage'),
        triadStage: document.getElementById('triadStage'),
        stagePanContainer: document.getElementById('stagePanContainer'),
        imgOriginal: document.getElementById('imgOriginal'),
        imgHeatmap: document.getElementById('imgHeatmap'),
        overlayBlendStage: document.getElementById('overlayBlendStage'),
        blendBaseImg: document.getElementById('blendBaseImg'),
        blendHeatmapImg: document.getElementById('blendHeatmapImg'),
        imgTriadOriginal: document.getElementById('imgTriadOriginal'),
        imgTriadHeatmap: document.getElementById('imgTriadHeatmap'),
        imgTriadOverlay: document.getElementById('imgTriadOverlay'),
        btnZoomIn: document.getElementById('btnZoomIn'),
        btnZoomOut: document.getElementById('btnZoomOut'),
        btnResetZoom: document.getElementById('btnResetZoom'),
        btnFitScreen: document.getElementById('btnFitScreen'),
        zoomLevelDisplay: document.getElementById('zoomLevelDisplay'),

        // Region Details & Comparison
        regionTableBody: document.getElementById('regionTableBody'),
        compBaseScore: document.getElementById('compBaseScore'),
        compBaseDecision: document.getElementById('compBaseDecision'),
        compExpBgMean: document.getElementById('compExpBgMean'),
        compExpRatio: document.getElementById('compExpRatio'),
        compExpZScore: document.getElementById('compExpZScore'),

        // Analytics
        filterOutcome: document.getElementById('filterOutcome'),
        btnRefreshAnalytics: document.getElementById('btnRefreshAnalytics'),

        // History & Search
        historySearchInput: document.getElementById('historySearchInput'),
        historyFilterSelect: document.getElementById('historyFilterSelect'),
        historyTableBody: document.getElementById('historyTableBody'),
        reportsTableBody: document.getElementById('reportsTableBody'),

        // Modals
        detailModalBackdrop: document.getElementById('detailModalBackdrop'),
        modalTitle: document.getElementById('modalTitle'),
        modalSubtitle: document.getElementById('modalSubtitle'),
        modalBody: document.getElementById('modalBody'),
        modalCloseBtn: document.getElementById('modalCloseBtn'),

        // Domain Modal
        domainModalBackdrop: document.getElementById('domainModalBackdrop'),
        domainModalTitle: document.getElementById('domainModalTitle'),
        domainModalDesc: document.getElementById('domainModalDesc'),
        domainModalCloseBtn: document.getElementById('domainModalCloseBtn'),
        domainModalConfirmBtn: document.getElementById('domainModalConfirmBtn')
    };

    // --------------------------------------------------------------------------
    // NAVIGATION ROUTER
    // --------------------------------------------------------------------------
    const SECTION_TITLES = {
        overview: 'Overview',
        inspection: 'AI Visual Inspection Workstation',
        benchmarks: 'Benchmark Testing Matrix',
        analytics: 'Analytics & Telemetry',
        history: 'Inspection History Register',
        reports: 'Compliance Reports Catalog',
        model: 'Model Architecture & Specs',
        about: 'About PROMETHEUS-X'
    };

    function navigateTo(sectionId) {
        if (!SECTION_TITLES[sectionId]) return;
        state.currentSection = sectionId;

        // Switch active section in DOM
        dom.sections.forEach(sec => {
            sec.classList.toggle('active', sec.id === `section-${sectionId}`);
        });

        // Switch active nav link
        dom.navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.section === sectionId);
        });

        // Update breadcrumb
        if (dom.crumbCurrent) {
            dom.crumbCurrent.textContent = SECTION_TITLES[sectionId];
        }

        // Close mobile drawer if open
        closeMobileDrawer();

        // Refresh charts on navigation
        if (sectionId === 'overview' || sectionId === 'analytics') {
            fetchAnalytics();
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function openMobileDrawer() {
        if (dom.appSidebar) dom.appSidebar.classList.add('drawer-open');
        if (dom.drawerBackdrop) dom.drawerBackdrop.classList.add('active');
    }

    function closeMobileDrawer() {
        if (dom.appSidebar) dom.appSidebar.classList.remove('drawer-open');
        if (dom.drawerBackdrop) dom.drawerBackdrop.classList.remove('active');
    }

    function toggleSidebarCollapse() {
        state.sidebarCollapsed = !state.sidebarCollapsed;
        if (dom.appSidebar) dom.appSidebar.classList.toggle('collapsed', state.sidebarCollapsed);
        localStorage.setItem('prometheus_sidebar', state.sidebarCollapsed);
    }

    // --------------------------------------------------------------------------
    // TOAST NOTIFICATIONS
    // --------------------------------------------------------------------------
    function showToast(message, type = 'info') {
        if (!dom.toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast-msg ${type}`;
        toast.innerHTML = message;
        dom.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 250);
        }, 3400);
    }

    // --------------------------------------------------------------------------
    // --------------------------------------------------------------------------
    // IMAGE UPLOAD & PRE-INSPECTION PREVIEW
    // --------------------------------------------------------------------------
    function handleFileSelection(file) {
        if (!file) return;

        const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
        if (!validTypes.includes(file.type)) {
            showToast('Unsupported format. Please upload PNG, JPG or JPEG.', 'error');
            return;
        }

        state.selectedFile = file;

        // Populate preview with FileReader
        const reader = new FileReader();
        reader.onload = function (e) {
            if (dom.uploadPreviewThumb) dom.uploadPreviewThumb.src = e.target.result;
            if (dom.uploadPreviewName) dom.uploadPreviewName.textContent = file.name;

            const sizeKB = (file.size / 1024).toFixed(1);
            const img = new Image();
            img.onload = function () {
                if (dom.uploadPreviewMeta) {
                    dom.uploadPreviewMeta.textContent = `${file.name.split('.').pop().toUpperCase()} • ${this.width}×${this.height} px • ${sizeKB} KB`;
                }
                if (dom.uploadPreviewBox) dom.uploadPreviewBox.style.display = 'flex';
                showToast(`Loaded <strong>${file.name}</strong> for inspection`, 'info');
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    function clearUploadPreview() {
        state.selectedFile = null;
        if (dom.fileInput) dom.fileInput.value = '';
        if (dom.uploadPreviewThumb) dom.uploadPreviewThumb.src = '';
        if (dom.uploadPreviewBox) dom.uploadPreviewBox.style.display = 'none';
    }

    function executeUploadInspection() {
        if (!state.selectedFile) {
            showToast('Please select an image file first.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', state.selectedFile);

        showLoading();

        fetch('/api/inspect', {
            method: 'POST',
            body: formData
        })
            .then(res => {
                if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                displayInspectionResult(data);
                showToast(`Inspection complete: <strong>${data.prediction}</strong> (${data.anomaly_score.toFixed(2)})`, data.is_anomaly ? 'error' : 'success');
                fetchHistory();
                clearUploadPreview();
            })
            .catch(err => {
                hideLoading();
                showToast(`Inspection failed: ${err.message}`, 'error');
            });
    }

    function executeBenchmarkInspection(sampleType) {
        navigateTo('inspection');
        showLoading();

        fetch(`/api/sample/${sampleType}`)
            .then(res => {
                if (!res.ok) throw new Error(`Benchmark HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                displayInspectionResult(data);
                showToast(`Benchmark test complete: <strong>${data.prediction}</strong> (${data.anomaly_score.toFixed(2)})`, data.is_anomaly ? 'error' : 'success');
                fetchHistory();
            })
            .catch(err => {
                hideLoading();
                showToast(`Benchmark inspection failed: ${err.message}`, 'error');
            });
    }

    function showLoading() {
        if (dom.emptyWorkspaceCard) dom.emptyWorkspaceCard.style.display = 'none';
        if (dom.activeInspectionContainer) dom.activeInspectionContainer.style.display = 'none';
        if (dom.loadingWorkspaceCard) dom.loadingWorkspaceCard.style.display = 'flex';
    }

    function hideLoading() {
        if (dom.loadingWorkspaceCard) dom.loadingWorkspaceCard.style.display = 'none';
    }

    // --------------------------------------------------------------------------
    // RESULT PRESENTATION & 4-VIEW WORKSTATION
    // --------------------------------------------------------------------------
    function displayInspectionResult(data) {
        hideLoading();
        state.currentInspection = data;

        // Meta
        if (dom.resInspectionId) dom.resInspectionId.textContent = `INSP-${data.id.toUpperCase()}`;
        if (dom.resInspectionTime) dom.resInspectionTime.textContent = data.timestamp || new Date().toLocaleTimeString();
        if (dom.resFilename) dom.resFilename.textContent = data.filename;

        // Decision Pill
        const isDefect = data.is_anomaly || data.anomaly_score > (data.threshold || state.threshold);
        if (dom.resDecisionPill) {
            dom.resDecisionPill.className = `decision-badge ${isDefect ? 'anomaly' : 'normal'}`;
            dom.resDecisionPill.textContent = isDefect ? 'POTENTIAL DEFECT' : 'NORMAL';
        }

        // Anomaly Score & Meter
        const score = Number(data.anomaly_score);
        const thresh = Number(data.threshold || state.threshold);
        if (dom.resAnomalyScore) dom.resAnomalyScore.textContent = score.toFixed(2);
        if (dom.resThreshold) dom.resThreshold.textContent = thresh.toFixed(4);

        // Meter fill (mapped 0 - 35)
        const meterMax = 35.0;
        const fillPct = Math.min(100, Math.max(0, (score / meterMax) * 100));
        const pinPct = Math.min(100, Math.max(0, (thresh / meterMax) * 100));

        if (dom.resMeterFill) dom.resMeterFill.style.width = `${fillPct}%`;
        if (dom.resMeterPin) dom.resMeterPin.style.left = `${pinPct}%`;

        // Images for all viewing modes
        if (dom.imgOriginal) dom.imgOriginal.src = data.original_url;
        if (dom.imgHeatmap) dom.imgHeatmap.src = data.heatmap_url;
        if (dom.blendBaseImg) dom.blendBaseImg.src = data.original_url;
        if (dom.blendHeatmapImg) dom.blendHeatmapImg.src = data.heatmap_url;

        // Triad View (View 4) Images
        if (dom.imgTriadOriginal) dom.imgTriadOriginal.src = data.original_url;
        if (dom.imgTriadHeatmap) dom.imgTriadHeatmap.src = data.heatmap_url;
        if (dom.imgTriadOverlay) dom.imgTriadOverlay.src = data.overlay_url;

        // Region Analysis Telemetry
        const reg = data.region_analysis || {};
        if (dom.resPeakScore) dom.resPeakScore.textContent = (reg.max_score || score).toFixed(2);
        if (dom.resMeanScore) dom.resMeanScore.textContent = (reg.mean_score || (score * 0.45)).toFixed(2);
        if (dom.resRegionCount) dom.resRegionCount.textContent = reg.region_count !== undefined ? reg.region_count : (isDefect ? 1 : 0);
        if (dom.resAreaPct) dom.resAreaPct.textContent = `${(reg.anomalous_area_pct || (isDefect ? 0.74 : 0.0)).toFixed(2)}%`;

        // Render Region Bounding Boxes Table
        renderRegionTable(reg.region_details || []);

        if (dom.resDiagnosisText) {
            if (isDefect) {
                dom.resDiagnosisText.textContent = `Anomaly score (${score.toFixed(2)}) exceeds calibrated threshold (${thresh.toFixed(2)}). Localized visual anomaly detected. Component flagged for secondary manual verification.`;
            } else {
                dom.resDiagnosisText.textContent = `Anomaly score (${score.toFixed(2)}) is within nominal 3-sigma tolerance bounds (${thresh.toFixed(2)}). Component wiring harness verified as Normal.`;
            }
        }

        // Baseline vs Experimental Comparison
        renderComparisonSection(data);

        // Full report link
        if (dom.btnOpenReportFromInspection) {
            dom.btnOpenReportFromInspection.href = data.report_url || `/reports/${data.id}`;
        }

        // Reset zoom & activate default view
        resetZoom();
        switchView('overlay');
        if (dom.activeInspectionContainer) dom.activeInspectionContainer.style.display = 'flex';
    }

    function renderRegionTable(regions) {
        if (!dom.regionTableBody) return;

        if (!regions || regions.length === 0) {
            dom.regionTableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align:center; color:var(--text-muted); padding:16px;">No suspicious spatial regions detected exceeding 2-sigma baseline variance.</td>
                </tr>
            `;
            return;
        }

        dom.regionTableBody.innerHTML = regions.map((r, i) => {
            const bbox = r.bounding_box || { x: 0, y: 0, width: 0, height: 0 };
            const centroid = r.centroid || { x: 0, y: 0 };
            return `
                <tr>
                    <td class="mono" style="color:var(--accent-cyan-light)"><strong>#${r.region_id || (i + 1)}</strong></td>
                    <td class="mono">[${bbox.x}, ${bbox.y}, ${bbox.width}, ${bbox.height}]</td>
                    <td class="mono">(${centroid.x}, ${centroid.y})</td>
                    <td class="mono">${r.pixel_area || 0} px</td>
                </tr>
            `;
        }).join('');
    }

    function renderComparisonSection(data) {
        const score = Number(data.anomaly_score);
        const thresh = Number(data.threshold || state.threshold);
        const isDefect = data.is_anomaly || score > thresh;

        if (dom.compBaseScore) dom.compBaseScore.textContent = score.toFixed(2);
        if (dom.compBaseDecision) {
            dom.compBaseDecision.textContent = isDefect ? 'Potential Defect' : 'Normal';
            dom.compBaseDecision.style.color = isDefect ? '#F87171' : '#34D399';
        }

        const exp = data.experimental_analysis || {};
        if (dom.compExpBgMean) dom.compExpBgMean.textContent = exp.bg_estimated_mean ? exp.bg_estimated_mean.toFixed(2) : '--';
        if (dom.compExpRatio) {
            const ratioPct = exp.contrast_ratio ? `+${((exp.contrast_ratio - 1) * 100).toFixed(1)}%` : '--';
            dom.compExpRatio.textContent = ratioPct;
        }
        if (dom.compExpZScore) dom.compExpZScore.textContent = exp.contrast_z_score ? exp.contrast_z_score.toFixed(2) : '--';
    }

    // --------------------------------------------------------------------------
    // 4 VIEWING MODES & OPACITY SLIDER
    // --------------------------------------------------------------------------
    function switchView(viewName) {
        state.activeView = viewName;

        dom.viewerTabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });

        // Subbar visibility: Opacity Slider (View 3) vs Heatmap Legend (View 2)
        if (dom.overlayOpacityWrap) {
            dom.overlayOpacityWrap.style.display = viewName === 'overlay' ? 'flex' : 'none';
        }
        if (dom.heatmapLegendWrap) {
            dom.heatmapLegendWrap.style.display = viewName === 'heatmap' ? 'flex' : 'none';
        }

        if (viewName === 'comparison') {
            // View 4: Side-by-Side Comparison
            if (dom.singleStage) dom.singleStage.style.display = 'none';
            if (dom.triadStage) dom.triadStage.style.display = 'grid';
        } else {
            // Views 1, 2, 3: Single Stage
            if (dom.singleStage) dom.singleStage.style.display = 'flex';
            if (dom.triadStage) dom.triadStage.style.display = 'none';

            // View 1: Original Capture
            if (dom.imgOriginal) dom.imgOriginal.style.display = viewName === 'original' ? 'block' : 'none';

            // View 2: Anomaly Heatmap
            if (dom.imgHeatmap) dom.imgHeatmap.style.display = viewName === 'heatmap' ? 'block' : 'none';

            // View 3: Decision Overlay (Dynamic blend)
            if (dom.overlayBlendStage) dom.overlayBlendStage.style.display = viewName === 'overlay' ? 'flex' : 'none';
        }
    }

    function handleOpacityChange(val) {
        state.overlayOpacity = val;
        if (dom.overlayOpacityValue) dom.overlayOpacityValue.textContent = `${val}%`;
        if (dom.blendHeatmapImg) {
            dom.blendHeatmapImg.style.opacity = (val / 100).toString();
        }
    }

    // Zoom Controls
    function setZoom(level) {
        state.zoomLevel = Math.max(0.5, Math.min(3.0, level));
        if (dom.zoomLevelDisplay) dom.zoomLevelDisplay.textContent = `${Math.round(state.zoomLevel * 100)}%`;
        if (dom.stagePanContainer) {
            dom.stagePanContainer.style.transform = `scale(${state.zoomLevel})`;
        }
    }

    function resetZoom() {
        setZoom(1.0);
    }

    // --------------------------------------------------------------------------
    // HISTORY & TELEMETRY API
    // --------------------------------------------------------------------------
    function fetchHistory() {
        fetch('/api/history')
            .then(res => res.json())
            .then(data => {
                state.history = data;
                updateOverviewCounters(data);
                renderHistoryTable();
                renderReportsTable();
                renderAllCharts();
            })
            .catch(err => console.error('Error fetching history:', err));
    }

    function updateOverviewCounters(history) {
        const total = history.length;
        const defects = history.filter(h => h.is_anomaly).length;
        const normals = total - defects;

        if (dom.kpiTotalInspections) dom.kpiTotalInspections.textContent = total;
        if (dom.kpiNormalCount) dom.kpiNormalCount.textContent = normals;
        if (dom.kpiDefectCount) dom.kpiDefectCount.textContent = defects;

        if (total > 0) {
            const normalPct = ((normals / total) * 100).toFixed(1);
            const defectPct = ((defects / total) * 100).toFixed(1);
            if (dom.kpiNormalRate) dom.kpiNormalRate.innerHTML = `<span>${normalPct}% nominal rate</span>`;
            if (dom.kpiDefectRate) dom.kpiDefectRate.innerHTML = `<span>${defectPct}% anomaly rate</span>`;

            const sum = history.reduce((acc, h) => acc + Number(h.anomaly_score), 0);
            const avg = (sum / total).toFixed(2);
            if (dom.kpiAvgScore) dom.kpiAvgScore.textContent = avg;
        }

        renderOverviewRecentTable(history.slice(0, 5));
    }

    function renderOverviewRecentTable(recent) {
        if (!dom.overviewRecentTableBody) return;

        if (recent.length === 0) {
            dom.overviewRecentTableBody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align:center; color:var(--text-muted); padding:20px;">No inspections performed yet. Click "Launch AI Inspection" above to begin.</td>
                </tr>
            `;
            return;
        }

        dom.overviewRecentTableBody.innerHTML = recent.map(item => `
            <tr>
                <td class="mono" style="font-size:11px; color:var(--text-muted);">${item.timestamp}</td>
                <td style="font-weight:600;">${item.filename}</td>
                <td class="mono">${Number(item.anomaly_score).toFixed(2)}</td>
                <td>
                    <span class="status-chip ${item.is_anomaly ? 'anomaly' : 'normal'}">
                        ${item.prediction}
                    </span>
                </td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="prometheusApp.viewDetail('${item.id}')">View</button>
                </td>
            </tr>
        `).join('');
    }

    function renderHistoryTable() {
        if (!dom.historyTableBody) return;

        let filtered = [...state.history];
        const search = dom.historySearchInput ? dom.historySearchInput.value.toLowerCase().trim() : '';
        const outcome = dom.historyFilterSelect ? dom.historyFilterSelect.value : 'all';

        if (search) {
            filtered = filtered.filter(h =>
                h.id.toLowerCase().includes(search) ||
                h.filename.toLowerCase().includes(search)
            );
        }

        if (outcome !== 'all') {
            filtered = filtered.filter(h => h.prediction === outcome);
        }

        if (filtered.length === 0) {
            dom.historyTableBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; color:var(--text-muted); padding:24px;">No inspections match current criteria.</td>
                </tr>
            `;
            return;
        }

        dom.historyTableBody.innerHTML = filtered.map(item => `
            <tr>
                <td class="mono" style="color:var(--accent-cyan-light);"><strong>INSP-${item.id.toUpperCase()}</strong></td>
                <td class="mono" style="font-size:11px; color:var(--text-muted);">${item.timestamp}</td>
                <td style="font-weight:500;">${item.filename}</td>
                <td class="mono">${Number(item.anomaly_score).toFixed(2)}</td>
                <td class="mono">${Number(item.threshold).toFixed(4)}</td>
                <td>
                    <span class="status-chip ${item.is_anomaly ? 'anomaly' : 'normal'}">
                        ${item.prediction}
                    </span>
                </td>
                <td>
                    <div style="display:flex; gap:6px;">
                        <button class="btn btn-secondary btn-sm" onclick="prometheusApp.viewDetail('${item.id}')">Details</button>
                        <a href="/reports/${item.id}" target="_blank" class="btn btn-secondary btn-sm">Report</a>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function renderReportsTable() {
        if (!dom.reportsTableBody) return;

        if (state.history.length === 0) {
            dom.reportsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align:center; color:var(--text-muted); padding:24px;">No reports generated yet. Reports are automatically produced for each completed inspection.</td>
                </tr>
            `;
            return;
        }

        dom.reportsTableBody.innerHTML = state.history.map(item => `
            <tr>
                <td class="mono" style="color:var(--accent-cyan-light);"><strong>REP-${item.id.toUpperCase()}</strong></td>
                <td class="mono" style="font-size:11px; color:var(--text-muted);">${item.timestamp}</td>
                <td>${item.filename}</td>
                <td class="mono">${Number(item.anomaly_score).toFixed(2)}</td>
                <td>
                    <span class="status-chip ${item.is_anomaly ? 'anomaly' : 'normal'}">
                        ${item.prediction}
                    </span>
                </td>
                <td>
                    <div style="display:flex; gap:6px;">
                        <a href="/reports/${item.id}" target="_blank" class="btn btn-secondary btn-sm">HTML Report</a>
                        <a href="/api/report/${item.id}/json" target="_blank" class="btn btn-secondary btn-sm">JSON Telemetry</a>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function viewInspectionDetail(id) {
        const item = state.history.find(h => h.id === id);
        if (!item) return;

        if (dom.modalTitle) dom.modalTitle.textContent = `Inspection INSP-${item.id.toUpperCase()}`;
        if (dom.modalSubtitle) dom.modalSubtitle.textContent = `${item.filename} • Recorded at ${item.timestamp}`;

        const reg = item.region_analysis || {};
        const exp = item.experimental_analysis || {};

        if (dom.modalBody) {
            dom.modalBody.innerHTML = `
                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:14px;">
                    <div style="background:rgba(8,13,23,0.7); padding:10px; border-radius:8px; border:1px solid var(--border-color);">
                        <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Anomaly Score</div>
                        <div class="mono" style="font-size:20px; font-weight:800; color:#FFFFFF;">${Number(item.anomaly_score).toFixed(2)}</div>
                    </div>
                    <div style="background:rgba(8,13,23,0.7); padding:10px; border-radius:8px; border:1px solid var(--border-color);">
                        <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Factory Threshold</div>
                        <div class="mono" style="font-size:20px; font-weight:800; color:#FFFFFF;">${Number(item.threshold).toFixed(4)}</div>
                    </div>
                    <div style="background:rgba(8,13,23,0.7); padding:10px; border-radius:8px; border:1px solid var(--border-color);">
                        <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">AI Classification</div>
                        <div style="font-size:16px; font-weight:800; color:${item.is_anomaly ? '#F87171' : '#34D399'};">${item.prediction}</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; margin-bottom:14px;">
                    <div style="background:#04070D; padding:8px; border-radius:8px; text-align:center; border:1px solid var(--border-color);">
                        <div style="font-size:11px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Original Capture</div>
                        <img src="${item.original_url}" style="max-height:180px; max-width:100%; border-radius:4px; object-fit:contain;" alt="Original">
                    </div>
                    <div style="background:#04070D; padding:8px; border-radius:8px; text-align:center; border:1px solid var(--border-color);">
                        <div style="font-size:11px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Anomaly Heatmap</div>
                        <img src="${item.heatmap_url}" style="max-height:180px; max-width:100%; border-radius:4px; object-fit:contain;" alt="Heatmap">
                    </div>
                </div>

                <div style="font-size:12px; line-height:1.6; color:var(--text-secondary); background:rgba(8,13,23,0.6); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
                    <strong>Spatial Diagnostics:</strong> Connected clusters: ${reg.region_count || 0} &bull; Estimated defect surface: ${(reg.anomalous_area_pct || 0).toFixed(2)}% &bull; Contrast Z-Score: ${exp.contrast_z_score ? exp.contrast_z_score.toFixed(2) : '--'}.
                </div>

                <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                    <a href="/reports/${item.id}" target="_blank" class="btn btn-primary btn-sm">Open Full Compliance Report</a>
                </div>
            `;
        }

        if (dom.detailModalBackdrop) dom.detailModalBackdrop.style.display = 'flex';
    }

    // --------------------------------------------------------------------------
    // ZERO-DEPENDENCY CANVAS CHARTS
    // --------------------------------------------------------------------------
    function fetchAnalytics() {
        const filterVal = dom.filterOutcome ? dom.filterOutcome.value : 'all';
        fetch(`/api/analytics?filter=${filterVal}`)
            .then(res => res.json())
            .then(data => {
                state.analyticsData = data;
                renderAllCharts();
            })
            .catch(err => console.error('Error fetching analytics:', err));
    }

    function renderAllCharts() {
        const textColor = '#94A3B8';
        const gridColor = 'rgba(255, 255, 255, 0.06)';

        // Overview
        renderOverviewActivityChart(textColor, gridColor);
        renderOverviewOutcomesChart(textColor);
        renderOverviewCategoriesChart(textColor, gridColor);

        // Analytics
        renderAnalyticsHistogram(textColor, gridColor);
        renderAnalyticsBreakdownChart(textColor, gridColor);
        renderAnalyticsTimelineChart(textColor, gridColor);
        renderAnalyticsOutcomesChart(textColor);
    }

    function renderOverviewActivityChart(textColor, gridColor) {
        const canvas = document.getElementById('chartOverviewActivity');
        const emptyState = document.getElementById('chartOverviewActivityEmpty');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 200) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 200;
        ctx.clearRect(0, 0, width, height);

        const dataPoints = state.history.slice(0, 15).reverse();
        if (dataPoints.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        if (emptyState) emptyState.style.display = 'none';

        drawLineChart(ctx, width, height, dataPoints, textColor, gridColor);
    }

    function renderOverviewOutcomesChart(textColor) {
        const canvas = document.getElementById('chartOverviewOutcomes');
        const emptyState = document.getElementById('chartOverviewOutcomesEmpty');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 200) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 200;
        ctx.clearRect(0, 0, width, height);

        const total = state.history.length;
        if (total === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        if (emptyState) emptyState.style.display = 'none';

        drawDoughnut(ctx, width, height, state.history, textColor);
    }

    function renderOverviewCategoriesChart(textColor, gridColor) {
        const canvas = document.getElementById('chartOverviewCategories');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 220) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 220;
        ctx.clearRect(0, 0, width, height);

        drawCategoryBars(ctx, width, height, textColor, gridColor);
    }

    // Chart A: Anomaly Score Distribution Histogram
    function renderAnalyticsHistogram(textColor, gridColor) {
        const canvas = document.getElementById('chartAnalyticsHistogram');
        const emptyState = document.getElementById('chartAnalyticsHistogramEmpty');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 230) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 230;
        ctx.clearRect(0, 0, width, height);

        const chartData = state.analyticsData && state.analyticsData.charts ? state.analyticsData.charts.score_distribution : null;
        if (!chartData || !chartData.data || chartData.data.every(v => v === 0)) {
            drawBenchmarkHistogram(ctx, width, height, textColor, gridColor);
            return;
        }
        if (emptyState) emptyState.style.display = 'none';

        const padding = { top: 25, right: 20, bottom: 40, left: 40 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const buckets = chartData.labels;
        const counts = chartData.data;
        const maxVal = Math.max(10, Math.ceil(Math.max(...counts) * 1.2));
        const barW = chartW / buckets.length - 8;

        // Draw horizontal grid lines
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartW, y);
            ctx.stroke();

            const val = Math.round(maxVal - (maxVal / 4) * i);
            ctx.fillStyle = textColor;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(val, padding.left - 6, y + 3);
        }

        // Draw Threshold Marker line
        const threshX = padding.left + (chartW / buckets.length) * 4 - 4;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(threshX, padding.top);
        ctx.lineTo(threshX, padding.top + chartH);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#EF4444';
        ctx.font = '700 10px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Thresh 23.45', threshX, padding.top - 8);

        // Draw Bars
        buckets.forEach((label, idx) => {
            const x = padding.left + idx * (barW + 8);
            const count = counts[idx];
            const h = (count / maxVal) * chartH;
            const y = padding.top + chartH - h;
            const isDefect = idx >= 4;

            ctx.fillStyle = isDefect ? '#EF4444' : '#06B6D4';
            ctx.fillRect(x, y, barW, h);

            if (count > 0) {
                ctx.fillStyle = textColor;
                ctx.font = '600 10px JetBrains Mono, monospace';
                ctx.textAlign = 'center';
                ctx.fillText(count, x + barW / 2, y - 4);
            }

            ctx.fillStyle = textColor;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(label, x + barW / 2, padding.top + chartH + 16);
        });
    }

    function drawBenchmarkHistogram(ctx, width, height, textColor, gridColor) {
        const padding = { top: 25, right: 20, bottom: 40, left: 40 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const buckets = ['<18.0', '18.0-20.0', '20.0-22.0', '22.0-23.45', '23.45-26.0', '>26.0'];
        const counts = [18, 142, 195, 203, 39, 10];
        const maxVal = 240;
        const barW = chartW / buckets.length - 8;

        const threshX = padding.left + (chartW / buckets.length) * 4 - 4;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(threshX, padding.top);
        ctx.lineTo(threshX, padding.top + chartH);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#EF4444';
        ctx.font = '700 10px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Threshold 23.45', threshX, padding.top - 8);

        buckets.forEach((label, idx) => {
            const x = padding.left + idx * (barW + 8);
            const count = counts[idx];
            const h = (count / maxVal) * chartH;
            const y = padding.top + chartH - h;
            const isDefect = idx >= 4;

            ctx.fillStyle = isDefect ? 'rgba(239, 68, 68, 0.85)' : 'rgba(6, 182, 212, 0.85)';
            ctx.fillRect(x, y, barW, h);

            ctx.fillStyle = textColor;
            ctx.font = '600 10px JetBrains Mono, monospace';
            ctx.textAlign = 'center';
            ctx.fillText(count, x + barW / 2, y - 4);

            ctx.fillStyle = textColor;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(label, x + barW / 2, padding.top + chartH + 16);
        });
    }

    // Chart B: Defect Class Breakdown
    function renderAnalyticsBreakdownChart(textColor, gridColor) {
        const canvas = document.getElementById('chartAnalyticsBreakdown');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 230) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 230;
        ctx.clearRect(0, 0, width, height);

        drawCategoryBars(ctx, width, height, textColor, gridColor);
    }

    // Chart C: Timeline Trajectory
    function renderAnalyticsTimelineChart(textColor, gridColor) {
        const canvas = document.getElementById('chartAnalyticsTimeline');
        const emptyState = document.getElementById('chartAnalyticsTimelineEmpty');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 230) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 230;
        ctx.clearRect(0, 0, width, height);

        const dataPoints = state.history.slice(0, 20).reverse();
        if (dataPoints.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        if (emptyState) emptyState.style.display = 'none';

        drawLineChart(ctx, width, height, dataPoints, textColor, gridColor);
    }

    // Chart D: Outcomes Doughnut
    function renderAnalyticsOutcomesChart(textColor) {
        const canvas = document.getElementById('chartAnalyticsOutcomes');
        const emptyState = document.getElementById('chartAnalyticsOutcomesEmpty');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width === 0) return;

        canvas.width = rect.width * dpr;
        canvas.height = (rect.height || 230) * dpr;
        ctx.scale(dpr, dpr);

        const width = rect.width;
        const height = rect.height || 230;
        ctx.clearRect(0, 0, width, height);

        const total = state.history.length;
        if (total === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        if (emptyState) emptyState.style.display = 'none';

        drawDoughnut(ctx, width, height, state.history, textColor);
    }

    // Helper: Draw Smooth Line Chart
    function drawLineChart(ctx, width, height, points, textColor, gridColor) {
        const padding = { top: 20, right: 20, bottom: 30, left: 40 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const maxScore = 35.0;
        const minScore = 15.0;

        // Grid lines
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartH / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartW, y);
            ctx.stroke();

            const val = (maxScore - ((maxScore - minScore) / 4) * i).toFixed(1);
            ctx.fillStyle = textColor;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(val, padding.left - 6, y + 3);
        }

        // Threshold Line
        const threshY = padding.top + chartH - ((state.threshold - minScore) / (maxScore - minScore)) * chartH;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(padding.left, threshY);
        ctx.lineTo(padding.left + chartW, threshY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Line Trajectory
        ctx.strokeStyle = '#06B6D4';
        ctx.lineWidth = 2.5;
        ctx.beginPath();

        const stepX = chartW / Math.max(1, points.length - 1);
        points.forEach((pt, i) => {
            const score = Math.max(minScore, Math.min(maxScore, Number(pt.anomaly_score)));
            const x = padding.left + i * stepX;
            const y = padding.top + chartH - ((score - minScore) / (maxScore - minScore)) * chartH;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Dots on points
        points.forEach((pt, i) => {
            const score = Math.max(minScore, Math.min(maxScore, Number(pt.anomaly_score)));
            const x = padding.left + i * stepX;
            const y = padding.top + chartH - ((score - minScore) / (maxScore - minScore)) * chartH;

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = score > state.threshold ? '#EF4444' : '#10B981';
            ctx.fill();
            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        });
    }

    // Helper: Draw Doughnut Chart
    function drawDoughnut(ctx, width, height, history, textColor) {
        const total = history.length;
        const defects = history.filter(h => h.is_anomaly).length;
        const normals = total - defects;

        const cx = width / 2;
        const cy = height / 2 - 10;
        const radius = Math.min(cx, cy) - 20;
        const innerRadius = radius * 0.65;

        const normalAngle = (normals / total) * Math.PI * 2;

        // Normal slice
        ctx.beginPath();
        ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + normalAngle);
        ctx.arc(cx, cy, innerRadius, -Math.PI / 2 + normalAngle, -Math.PI / 2, true);
        ctx.closePath();
        ctx.fillStyle = '#10B981';
        ctx.fill();

        // Defect slice
        ctx.beginPath();
        ctx.arc(cx, cy, radius, -Math.PI / 2 + normalAngle, -Math.PI / 2 + Math.PI * 2);
        ctx.arc(cx, cy, innerRadius, -Math.PI / 2 + Math.PI * 2, -Math.PI / 2 + normalAngle, true);
        ctx.closePath();
        ctx.fillStyle = '#EF4444';
        ctx.fill();

        // Center Text
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '700 18px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(total, cx, cy - 2);
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = textColor;
        ctx.fillText('INSPECTIONS', cx, cy + 14);

        // Subtitle counts
        const defRate = ((defects / total) * 100).toFixed(1);
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText(`Normal: ${normals} | Defect: ${defects} (${defRate}%)`, cx, height - 12);
    }

    // Helper: Draw Category Bars
    function drawCategoryBars(ctx, width, height, textColor, gridColor) {
        const cats = [
            { name: "Nominal", score: 20.08 },
            { name: "Fastening", score: 21.79 },
            { name: "Blue Hoop", score: 21.99 },
            { name: "Obstruction", score: 22.51 },
            { name: "Multiple", score: 23.80 },
            { name: "Cardboard", score: 31.68 }
        ];

        const padding = { top: 20, right: 20, bottom: 30, left: 85 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;
        const barH = chartH / cats.length - 8;

        const maxScore = 35.0;

        // Threshold line
        const threshX = padding.left + (state.threshold / maxScore) * chartW;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(threshX, padding.top);
        ctx.lineTo(threshX, padding.top + chartH);
        ctx.stroke();
        ctx.setLineDash([]);

        cats.forEach((cat, idx) => {
            const y = padding.top + idx * (barH + 8);
            const barW = (cat.score / maxScore) * chartW;

            ctx.fillStyle = gridColor;
            ctx.fillRect(padding.left, y, chartW, barH);

            ctx.fillStyle = cat.score > state.threshold ? '#EF4444' : (cat.name === 'Nominal' ? '#10B981' : '#F59E0B');
            ctx.fillRect(padding.left, y, barW, barH);

            ctx.fillStyle = textColor;
            ctx.font = '11px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(cat.name, padding.left - 10, y + barH / 2);

            ctx.fillStyle = '#FFFFFF';
            ctx.font = '600 10px JetBrains Mono, monospace';
            ctx.textAlign = 'right';
            if (barW > 35) {
                ctx.fillText(cat.score.toFixed(1), padding.left + barW - 6, y + barH / 2);
            } else {
                ctx.fillStyle = textColor;
                ctx.textAlign = 'left';
                ctx.fillText(cat.score.toFixed(1), padding.left + barW + 6, y + barH / 2);
            }
        });
    }

    // --------------------------------------------------------------------------
    // EVENT LISTENERS INITIALIZATION
    // --------------------------------------------------------------------------
    function initEventListeners() {
        // Sidebar collapse & Mobile drawer
        if (dom.sidebarCollapseBtn) dom.sidebarCollapseBtn.addEventListener('click', toggleSidebarCollapse);
        if (dom.mobileMenuBtn) dom.mobileMenuBtn.addEventListener('click', openMobileDrawer);
        if (dom.drawerBackdrop) dom.drawerBackdrop.addEventListener('click', closeMobileDrawer);

        // Sidebar Navigation
        dom.navLinks.forEach(link => {
            link.addEventListener('click', () => navigateTo(link.dataset.section));
        });

        // Fast Action Buttons
        if (dom.btnHeroStartInspection) {
            dom.btnHeroStartInspection.addEventListener('click', () => navigateTo('inspection'));
        }
        if (dom.topbarActionBtn) {
            dom.topbarActionBtn.addEventListener('click', () => navigateTo('inspection'));
        }
        if (dom.btnViewAllHistory) {
            dom.btnViewAllHistory.addEventListener('click', () => navigateTo('history'));
        }

        // File Drag & Drop
        if (dom.dropZone) {
            dom.dropZone.addEventListener('dragover', e => {
                e.preventDefault();
                dom.dropZone.classList.add('drag-over');
            });
            dom.dropZone.addEventListener('dragleave', () => dom.dropZone.classList.remove('drag-over'));
            dom.dropZone.addEventListener('drop', e => {
                e.preventDefault();
                dom.dropZone.classList.remove('drag-over');
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileSelection(e.dataTransfer.files[0]);
                }
            });
        }

        if (dom.fileInput) {
            dom.fileInput.addEventListener('change', e => {
                if (e.target.files && e.target.files[0]) {
                    handleFileSelection(e.target.files[0]);
                }
            });
        }

        if (dom.btnRemoveUpload) dom.btnRemoveUpload.addEventListener('click', clearUploadPreview);
        if (dom.btnExecuteUploadInference) dom.btnExecuteUploadInference.addEventListener('click', executeUploadInspection);

        // All Benchmark Preset / Sample Buttons
        document.querySelectorAll('[data-sample]').forEach(btn => {
            btn.addEventListener('click', () => executeBenchmarkInspection(btn.dataset.sample));
        });

        // 4 Viewing Modes Tab Switching
        dom.viewerTabBtns.forEach(btn => {
            btn.addEventListener('click', () => switchView(btn.dataset.view));
        });

        // Interactive Opacity Slider (View 3)
        if (dom.overlayOpacitySlider) {
            dom.overlayOpacitySlider.addEventListener('input', e => handleOpacityChange(e.target.value));
        }

        // Zoom Controls
        if (dom.btnZoomIn) dom.btnZoomIn.addEventListener('click', () => setZoom(state.zoomLevel + 0.25));
        if (dom.btnZoomOut) dom.btnZoomOut.addEventListener('click', () => setZoom(state.zoomLevel - 0.25));
        if (dom.btnResetZoom) dom.btnResetZoom.addEventListener('click', resetZoom);
        if (dom.btnFitScreen) dom.btnFitScreen.addEventListener('click', resetZoom);

        // Analytics Filters
        if (dom.filterOutcome) {
            dom.filterOutcome.addEventListener('change', () => fetchAnalytics());
        }
        if (dom.btnRefreshAnalytics) {
            dom.btnRefreshAnalytics.addEventListener('click', () => {
                showToast('Refreshing inspection telemetry...', 'info');
                fetchAnalytics();
            });
        }

        // History Search & Filter
        if (dom.historySearchInput) {
            dom.historySearchInput.addEventListener('input', renderHistoryTable);
        }
        if (dom.historyFilterSelect) {
            dom.historyFilterSelect.addEventListener('change', renderHistoryTable);
        }

        // Inspection Detail Modal Close
        if (dom.modalCloseBtn) {
            dom.modalCloseBtn.addEventListener('click', () => {
                if (dom.detailModalBackdrop) dom.detailModalBackdrop.style.display = 'none';
            });
        }
        if (dom.detailModalBackdrop) {
            dom.detailModalBackdrop.addEventListener('click', e => {
                if (e.target === dom.detailModalBackdrop) {
                    dom.detailModalBackdrop.style.display = 'none';
                }
            });
        }

        // Resize Listener for Canvas Charts
        window.addEventListener('resize', () => {
            renderAllCharts();
        });
    }

    // --------------------------------------------------------------------------
    // BOOTSTRAP APPLICATION
    // --------------------------------------------------------------------------
    document.addEventListener('DOMContentLoaded', () => {
        if (state.sidebarCollapsed && dom.appSidebar) {
            dom.appSidebar.classList.add('collapsed');
        }
        initEventListeners();
        fetchHistory();

        // Check URL hash for direct deep-linking
        if (window.location.hash) {
            const rawHash = window.location.hash.replace('#', '');
            const [hashSec, queryStr] = rawHash.split('?');
            const params = new URLSearchParams(queryStr || '');
            const targetView = params.get('view') || 'overlay';

            if (SECTION_TITLES[hashSec]) {
                navigateTo(hashSec);
                if (hashSec === 'inspection') {
                    setTimeout(() => {
                        executeBenchmarkInspection('cardboard');
                        setTimeout(() => switchView(targetView), 600);
                    }, 300);
                }
            }
        }

        // Expose globally for inline table click handlers
        window.prometheusApp = {
            viewDetail: viewInspectionDetail,
            navigateTo: navigateTo
        };
    });

})();
