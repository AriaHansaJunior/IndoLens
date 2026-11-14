/**
 * IndoLens - Real-Time YOLO Face Detection & Actor Recognition
 * Integrates live camera frames with YOLOv8 face detection,
 * FaceNet 512-D embeddings, Euclidean matching (threshold 0.85),
 * and frame-difference play/pause state detection.
 */

const CameraCapture = {
    mediaStream: null,
    currentFacingMode: 'environment',
    activeFacingMode: 'environment',
    isStreaming: false,

    // Frame Pipeline State
    isPipelineActive: false,
    pipelineIntervalId: null,
    pipelineTargetFps: 10,
    pipelineStartTime: null,
    totalFramesIngested: 0,
    totalManualSnapshots: 0,

    // Reusable Canvas Buffers
    bufferCanvas: null,
    bufferCtx: null,
    yoloCanvas: null,
    yoloCtx: null,
    YOLO_SEND_MAX_WIDTH: 640,

    // YOLO + FaceNet Detection State
    detectionCanvas: null,
    detectionCtx: null,
    isDetectionInFlight: false,
    latestDetections: [],
    facesDetectedCount: 0,
    lastYoloInferenceMs: 0,
    lastFaceNetLatencyMs: 0,
    facenetProcessedCount: 0,
    actorDbCache: {},
    lastActiveSyncTime: 0,

    // Frame-Difference Video State
    videoState: 'idle',
    prevFrameData: null,
    consecutiveStableFrames: 0,
    PAUSE_DIFF_THRESHOLD: 3.2,
    PAUSE_CONSECUTIVE_REQUIRED: 4,

    // Dedicated Latest Frame Buffer (Ready for future AI processing)
    latestFrame: {
        frameNumber: 0,
        timestamp: null,
        width: 0,
        height: 0,
        canvas: null,
        status: 'IDLE', // 'IDLE' | 'READY_FOR_YOLO' | 'YOLO_DETECTING'
    },

    // DOM Elements Cache
    elements: {},

    /**
     * Entry Point
     */
    init() {
        this.cacheDOM();
        this.initBufferCanvas();
        this.initDetectionCanvas();
        this.bindEvents();
        this.checkDeviceSupport();
        this.exposePipelineAPI();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            video: document.getElementById('cameraVideo'),
            detectionCanvas: document.getElementById('detectionCanvas'),
            canvas: document.getElementById('captureCanvas'),
            placeholder: document.getElementById('cameraPlaceholder'),
            overlay: document.getElementById('viewfinderOverlay'),
            overlayPill: document.getElementById('videoOverlayPill'),
            overlayResolution: document.getElementById('overlayResolution'),
            overlayFacingMode: document.getElementById('overlayFacingMode'),
            errorBanner: document.getElementById('cameraErrorBanner'),
            errorMessage: document.getElementById('cameraErrorMessage'),

            statusBadge: document.getElementById('cameraStatusBadge'),
            statusText: document.getElementById('cameraStatusText'),
            btnToggle: document.getElementById('btnToggleCamera'),
            btnToggleText: document.getElementById('btnToggleText'),
            btnSwitch: document.getElementById('btnSwitchCamera'),
            btnCapture: document.getElementById('btnCaptureFrame'),
            btnStartPrompt: document.getElementById('btnStartPrompt'),

            statFacesCount: document.getElementById('statFacesCount'),
            statYoloLatency: document.getElementById('statYoloLatency'),
            statFaceNetLatency: document.getElementById('statFaceNetLatency'),

            videoStatePill: document.getElementById('videoStatePill'),
            videoStateIcon: document.getElementById('videoStateIcon'),
            videoStateText: document.getElementById('videoStateText'),
            pauseActionOverlay: document.getElementById('pauseActionOverlay'),
        };
    },

    /**
     * Initialize Dedicated Offscreen Frame Buffer Canvas
     * Also initializes the YOLO downsampling canvas (separate from viewfinder buffer).
     */
    initBufferCanvas() {
        this.bufferCanvas = document.createElement('canvas');
        this.bufferCtx = this.bufferCanvas.getContext('2d', { willReadFrequently: true });
        this.latestFrame.canvas = this.bufferCanvas;

        // YOLO canvas: fixed-width offscreen canvas for fast payload to Python service.
        // Viewfinder is NOT affected — only inference input is downsampled.
        // Session 7: willReadFrequently=true for efficient getImageData in frame-difference
        this.yoloCanvas = document.createElement('canvas');
        this.yoloCtx = this.yoloCanvas.getContext('2d', { willReadFrequently: true });
    },

    /**
     * Initialize Viewfinder Bounding Box Overlay Canvas
     */
    initDetectionCanvas() {
        this.detectionCanvas = this.elements.detectionCanvas;
        if (this.detectionCanvas) {
            this.detectionCtx = this.detectionCanvas.getContext('2d');
        }
    },

    /**
     * Bind UI & Lifecycle Event Listeners
     */
    bindEvents() {
        if (this.elements.btnToggle) {
            this.elements.btnToggle.addEventListener('click', () => this.toggleCamera());
        }

        if (this.elements.btnStartPrompt) {
            this.elements.btnStartPrompt.addEventListener('click', () => this.startCamera());
        }

        if (this.elements.btnSwitch) {
            this.elements.btnSwitch.addEventListener('click', () => this.switchCamera());
        }

        if (this.elements.btnCapture) {
            this.elements.btnCapture.addEventListener('click', () => this.captureManualSnapshot());
        }

        // Clean resource release on page unload / navigation
        window.addEventListener('beforeunload', () => {
            this.stopCamera();
        });

        window.addEventListener('pagehide', () => {
            this.stopCamera();
        });

        // Pause / Resume pipeline frame ingestion on tab visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                if (this.isPipelineActive) {
                    this.pausePipelineForVisibility();
                }
            } else {
                if (this.isStreaming && !this.isPipelineActive) {
                    this.startPipeline();
                }
            }
        });

        // Resize detection canvas when window / viewport resizes
        window.addEventListener('resize', () => {
            if (this.isStreaming && this.latestDetections.length > 0) {
                this.renderBoundingBoxes(this.latestDetections);
            }
        });
    },

    /**
     * Expose Global IndoLens Pipeline Interface for Inspection and Future Sessions
     */
    exposePipelineAPI() {
        window.IndoLensPipeline = {
            getLatestFrame: () => this.getLatestFrame(),
            getLatestDetections: () => this.latestDetections,
            getFacesCount: () => this.facesDetectedCount,
            isReady: () => this.isPipelineReady(),
            getStatus: () => ({
                isStreaming: this.isStreaming,
                isPipelineActive: this.isPipelineActive,
                totalFramesIngested: this.totalFramesIngested,
                facingMode: this.currentFacingMode,
                frameNumber: this.latestFrame.frameNumber,
                status: this.latestFrame.status,
                facesDetected: this.facesDetectedCount,
                yoloInferenceMs: this.lastYoloInferenceMs,
                facenetLatencyMs: this.lastFaceNetLatencyMs,
                facenetProcessedCount: this.facenetProcessedCount,
                videoState: this.videoState, // Session 7
            })
        };
    },

    /**
     * Check browser mediaDevices support
     */
    checkDeviceSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError('Camera access is not supported by this browser. Please use a modern browser (Chrome, Safari, Edge, Firefox) with HTTPS or localhost.');
            if (this.elements.btnToggle) this.elements.btnToggle.disabled = true;
            if (this.elements.btnStartPrompt) this.elements.btnStartPrompt.disabled = true;
        }
    },

    /**
     * Start / Stop Camera Toggle
     */
    async toggleCamera() {
        if (this.isStreaming) {
            this.stopCamera();
        } else {
            await this.startCamera();
        }
    },

    /**
     * Start Camera Stream & Real-Time Pipeline
     */
    async startCamera() {
        this.hideError();
        this.updateStatus('connecting', 'Connecting...');

        // Prefer 4:3 at 2048×1536 for phone sensor alignment — lower processing cost vs full 4096×3072
        const constraints = {
            audio: false,
            video: {
                facingMode: { ideal: this.currentFacingMode },
                width: { ideal: 2048 },
                height: { ideal: 1536 },
            }
        };

        try {
            try {
                this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (err) {
                console.warn('Primary 4:3 constraint failed, falling back to 4:3 at lower resolution:', err);
                try {
                    this.mediaStream = await navigator.mediaDevices.getUserMedia({
                        audio: false,
                        video: { facingMode: { ideal: this.currentFacingMode }, width: { ideal: 1024 }, height: { ideal: 768 } }
                    });
                } catch (err2) {
                    this.mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                }
            }

            const video = this.elements.video;
            video.muted = true;
            video.playsInline = true;
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');
            video.srcObject = this.mediaStream;

            // Make video visible so mobile Chrome compositor decodes video frames
            video.style.display = 'block';

            // Wait for video metadata/play with multi-event and safety timeout fallback
            await new Promise((resolve) => {
                let resolved = false;
                const onReady = () => {
                    if (!resolved) {
                        resolved = true;
                        video.play().catch(e => console.warn('video.play notice:', e)).finally(resolve);
                    }
                };

                // If already ready
                if (video.readyState >= 1 && video.videoWidth > 0) {
                    onReady();
                    return;
                }

                video.addEventListener('loadedmetadata', onReady, { once: true });
                video.addEventListener('loadeddata', onReady, { once: true });
                video.addEventListener('canplay', onReady, { once: true });

                // Safety timeout fallback: never hang indefinitely on mobile
                setTimeout(onReady, 600);
            });

            this.isStreaming = true;
            this.onStreamStarted();

        } catch (error) {
            console.error('Camera access error:', error);
            this.isStreaming = false;
            this.handleCameraError(error);
        }
    },

    /**
     * Callback when video stream successfully begins
     */
    onStreamStarted() {
        const video = this.elements.video;
        const width = video.videoWidth || 1280;
        const height = video.videoHeight || 720;

        // Resize buffer canvas to match stream dimensions
        this.bufferCanvas.width = width;
        this.bufferCanvas.height = height;

        // Read active camera track info first (needed for mirror logic below)
        const track = this.mediaStream.getVideoTracks()[0];
        const trackSettings = track ? track.getSettings() : {};
        const deviceLabel = track ? (track.label || 'Connected Camera') : 'Default Camera';
        const activeFacing = trackSettings.facingMode || this.currentFacingMode;

        // UI State Transitions
        if (this.elements.placeholder) this.elements.placeholder.style.display = 'none';
        if (video) video.style.display = 'block';
        if (this.detectionCanvas) this.detectionCanvas.style.display = 'block';
        if (this.elements.overlay) this.elements.overlay.style.display = 'block';
        if (this.elements.overlayPill) this.elements.overlayPill.style.display = 'flex';

        // Apply front camera mirror ONLY to video.
        // Canvas is left unmirrored so text reads normally; coordinates are flipped mathematically.
        this.activeFacingMode = activeFacing;
        const isFrontCamera = activeFacing === 'user';
        const mirrorTransform = isFrontCamera ? 'scaleX(-1)' : '';
        if (video) video.style.transform = mirrorTransform;
        if (this.detectionCanvas) this.detectionCanvas.style.transform = '';

        // Enable action buttons
        if (this.elements.btnSwitch) this.elements.btnSwitch.disabled = false;
        if (this.elements.btnCapture) this.elements.btnCapture.disabled = false;

        // Update toggle button appearance
        if (this.elements.btnToggle) {
            this.elements.btnToggle.classList.remove('btn-start');
            this.elements.btnToggle.classList.add('btn-stop');
            if (this.elements.btnToggleText) this.elements.btnToggleText.textContent = 'Stop Camera';
        }

        if (this.elements.overlayResolution) this.elements.overlayResolution.textContent = `${width} × ${height}`;
        if (this.elements.overlayFacingMode) {
            this.elements.overlayFacingMode.textContent = activeFacing === 'user' ? 'Front (User)' : 'Rear (Environment)';
        }

        this.startPipeline();
    },

    startPipeline() {
        if (!this.isStreaming || this.isPipelineActive) return;

        this.isPipelineActive = true;
        this.pipelineStartTime = performance.now();
        this.totalFramesIngested = 0;
        this.isDetectionInFlight = false;

        this.prevFrameData = null;
        this.consecutiveStableFrames = 0;
        this.setVideoState('idle');

        this.updateStatus('streaming', 'Pipeline Active');

        if (this.elements.videoStatePill) {
            this.elements.videoStatePill.style.display = 'flex';
        }

        const intervalMs = Math.round(1000 / this.pipelineTargetFps); // ~100ms for 10 FPS

        // Controlled acquisition and detection timer
        this.pipelineIntervalId = setInterval(() => {
            this.acquireFrame();
        }, intervalMs);
    },

    /**
     * Acquire Next Frame into Latest Frame Buffer and Dispatch to YOLO
     */
    acquireFrame() {
        if (!this.isStreaming || !this.isPipelineActive) return;

        const video = this.elements.video;
        if (!video || video.readyState < 2) return;

        const width = video.videoWidth;
        const height = video.videoHeight;
        if (!width || !height) return;

        // Ensure buffer dimensions match video
        if (this.bufferCanvas.width !== width || this.bufferCanvas.height !== height) {
            this.bufferCanvas.width = width;
            this.bufferCanvas.height = height;
        }

        // The full-res bufferCtx is intentionally NOT drawn continuously here
        // to prevent extreme mobile CPU/GPU throttling (3.1M pixels at 10 FPS).
        // Manual capture (captureManualSnapshot) draws from the video directly.

        // 1. Downsample into dedicated YOLO canvas (reduces JPEG payload ~10x for 2048→640)
        const yoloW = Math.min(width, this.YOLO_SEND_MAX_WIDTH);
        const yoloH = Math.round(height * (yoloW / width));
        if (this.yoloCanvas.width !== yoloW || this.yoloCanvas.height !== yoloH) {
            this.yoloCanvas.width = yoloW;
            this.yoloCanvas.height = yoloH;
        }
        this.yoloCtx.drawImage(video, 0, 0, yoloW, yoloH);

        // Frame-Difference State Detection
        this.computeFrameDifference(yoloW, yoloH);

        this.totalFramesIngested++;
        this.latestFrame.frameNumber = this.totalFramesIngested;
        this.latestFrame.timestamp = Date.now();
        this.latestFrame.captureTime = performance.now();
        this.latestFrame.width = width;
        this.latestFrame.height = height;
        this.latestFrame.status = 'READY_FOR_YOLO';

        const newFrame = this.getLatestFrame();
        this.pendingYoloFrame = newFrame;

        if (!this.isDetectionInFlight) {
            this.triggerYoloDetection();
        }
    },

    /**
     * Compare current yoloCanvas pixels against previous frame to detect running vs paused video.
     */
    computeFrameDifference(yoloW, yoloH) {
        const currentImageData = this.yoloCtx.getImageData(0, 0, yoloW, yoloH);
        const currentData = currentImageData.data;

        if (!this.prevFrameData || this.prevFrameData.length !== currentData.length) {
            this.prevFrameData = new Uint8ClampedArray(currentData.length);
            this.prevFrameData.set(currentData);
            this.consecutiveStableFrames = 0;
            if (this.videoState === 'idle') {
                this.setVideoState('running');
            }
            return;
        }

        // Strided RGB sampling (every 8th pixel)
        const stride = 8 * 4;
        let totalDiff = 0;
        let sampleCount = 0;

        for (let i = 0; i < currentData.length; i += stride) {
            totalDiff += Math.abs(currentData[i] - this.prevFrameData[i]);
            totalDiff += Math.abs(currentData[i + 1] - this.prevFrameData[i + 1]);
            totalDiff += Math.abs(currentData[i + 2] - this.prevFrameData[i + 2]);
            sampleCount += 3;
        }

        const meanDiff = sampleCount > 0 ? totalDiff / sampleCount : 0;

        this.prevFrameData.set(currentData);

        if (meanDiff <= this.PAUSE_DIFF_THRESHOLD) {
            this.consecutiveStableFrames++;
            if (this.consecutiveStableFrames >= this.PAUSE_CONSECUTIVE_REQUIRED && this.videoState !== 'paused') {
                this.setVideoState('paused');
            }
        } else {
            this.consecutiveStableFrames = 0;
            if (this.videoState !== 'running') {
                this.setVideoState('running');
            }
        }
    },

    /**
     * Update video running/paused state and overlay UI.
     */
    setVideoState(state) {
        const prevState = this.videoState;
        this.videoState = state;

        // Update Video State Pill
        const pill = this.elements.videoStatePill;
        if (pill) {
            pill.classList.remove('running', 'paused');

            if (state === 'running') {
                pill.classList.add('running');
                if (this.elements.videoStateIcon) this.elements.videoStateIcon.textContent = '▶';
                if (this.elements.videoStateText) this.elements.videoStateText.textContent = 'Video Running';
            } else if (state === 'paused') {
                pill.classList.add('paused');
                if (this.elements.videoStateIcon) this.elements.videoStateIcon.textContent = '⏸';
                if (this.elements.videoStateText) this.elements.videoStateText.textContent = 'Video Paused';
            } else {
                if (this.elements.videoStateIcon) this.elements.videoStateIcon.textContent = '▶';
                if (this.elements.videoStateText) this.elements.videoStateText.textContent = 'Idle';
            }
        }

        if (state === 'paused') {
            this.showPauseActionOverlay();
        } else {
            this.hidePauseActionOverlay();
        }
    },

    showPauseActionOverlay() {
        const overlay = this.elements.pauseActionOverlay;
        if (!overlay) return;

        const knownWithRecords = (this.latestDetections || []).filter(
            f => f.status === 'known' && f.db_record && f.db_record.uuid
        );

        if (knownWithRecords.length === 0) {
            overlay.style.display = 'none';
            overlay.innerHTML = '';
            return;
        }

        const seenActorUuids = new Set();
        const uniqueKnownFaces = [];
        for (const face of knownWithRecords) {
            if (!seenActorUuids.has(face.db_record.uuid)) {
                seenActorUuids.add(face.db_record.uuid);
                uniqueKnownFaces.push(face);
            }
        }

        let html = '';
        for (const known of uniqueKnownFaces) {
            const actorName = known.actor || known.db_record.full_name || 'Unknown Actor';
            const actorUuid = known.db_record.uuid;
            const distStr = typeof known.distance === 'number' && known.distance < 900
                ? known.distance.toFixed(3)
                : '-';

            html += `
                <div class="pause-action-card">
                    <div class="pause-action-header">
                        <span class="pause-action-dot"></span>
                        <span class="pause-action-actor-name">${this.escapeHtml(actorName)}</span>
                    </div>
                    <span class="pause-action-status">Recognized · Distance ${distStr}</span>
                    <a href="/actors/${actorUuid}" class="pause-action-btn">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                        Open Actor Detail
                    </a>
                </div>
            `;
        }

        overlay.innerHTML = html;
        overlay.style.display = 'flex';

        const activeNames = uniqueKnownFaces.map(f => f.db_record.full_name || f.actor);
        this.syncActiveActors(activeNames);
    },

    /**
     * Synchronize detected known actors to MySQL (/api/actors/active).
     */
    async syncActiveActors(actorNames = []) {
        try {
            const cleanNames = [...new Set((actorNames || []).filter(n => n && n !== 'Unknown' && n !== 'Tidak Dikenali'))];
            await fetch('/api/actors/active', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify({ actors: cleanNames })
            });
            this.lastActiveSyncTime = performance.now();
        } catch (e) {
            console.warn('[Active Actor Sync Notice]', e.message);
        }
    },

    /**
     * Hide and clear pause action overlay.
     */
    hidePauseActionOverlay() {
        const overlay = this.elements.pauseActionOverlay;
        if (overlay) {
            overlay.style.display = 'none';
            overlay.innerHTML = '';
        }
    },

    /**
     * Escape HTML entities to prevent XSS in overlay cards.
     */
    escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    },

    /**
     * Send Latest Frame to YOLO Face Detection Endpoint
     * Endpoint: POST /api/yolo/detect (proxied to Python micro-service)
     * Retrieves latest frame from window.IndoLensPipeline.getLatestFrame()
     */
    async triggerYoloDetection() {
        if (!this.isStreaming || !this.isPipelineActive || this.isDetectionInFlight) return;
        if (!this.pendingYoloFrame) return;

        // Consume the newest pending frame and discard any older ones automatically
        const frame = this.pendingYoloFrame;
        this.pendingYoloFrame = null;

        if (!frame || !frame.canvas || !frame.width || !frame.height) return;

        this.isDetectionInFlight = true;

        try {
            // Downsampled JPEG for fast mobile transfer
            const blob = await new Promise((resolve) =>
                this.yoloCanvas.toBlob(resolve, 'image/jpeg', 0.70)
            );

            if (!blob || !this.isStreaming || !this.isPipelineActive) {
                this.isDetectionInFlight = false;
                return;
            }

            const t_req_sent = performance.now();
            const response = await fetch('/api/yolo/detect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'image/jpeg',
                },
                body: blob
            });
            const t_yolo_resp = performance.now();

            if (!response.ok) {
                throw new Error(`YOLO detection failed (HTTP ${response.status})`);
            }

            const data = await response.json();

            if (data.status === 'success' && this.isStreaming && this.isPipelineActive) {
                this.latestDetections = data.faces || [];
                this.facesDetectedCount = data.faces_count || 0;
                this.facenetProcessedCount = data.facenet_processed_count || 0;
                this.lastYoloInferenceMs = data.inference_time_ms || Math.round(t_yolo_resp - t_req_sent);
                this.lastFaceNetLatencyMs = data.facenet_time_ms || 0;

                // Update telemetry fields (including FaceNet vector status)
                this.updateYoloTelemetry(
                    this.facesDetectedCount,
                    this.lastYoloInferenceMs,
                    this.lastFaceNetLatencyMs,
                    this.latestDetections
                );

                // Resolve recognized known actors against MySQL
                await this.resolveKnownActors(this.latestDetections);

                this.renderBoundingBoxes(this.latestDetections, data.frame_dimensions);
                this.renderDetectedFacesList(this.latestDetections);

                if (this.videoState === 'paused') {
                    this.showPauseActionOverlay();
                } else {
                    // Throttled MySQL active actor sync (~1.5s)
                    const liveKnown = (this.latestDetections || []).filter(f => f.status === 'known' && f.db_record && f.db_record.full_name);
                    if (liveKnown.length > 0 && (performance.now() - this.lastActiveSyncTime > 1500)) {
                        const names = [...new Set(liveKnown.map(f => f.db_record.full_name))];
                        this.syncActiveActors(names);
                    }
                }
            }
        } catch (err) {
            console.warn('[YOLO Detection Notice]', err.message);
        } finally {
            this.isDetectionInFlight = false;

            if (this.pendingYoloFrame) {
                this.triggerYoloDetection();
            }
        }
    },

    /**
     * Resolve recognized known faces against MySQL (/api/actors/lookup).
     */
    async resolveKnownActors(faces) {
        if (!faces || faces.length === 0) return;

        const knownFaces = faces.filter(f => f.status === 'known' && f.actor && f.actor !== 'Unknown');
        if (knownFaces.length === 0) return;

        const now = performance.now();
        for (const face of knownFaces) {
            const actorName = face.actor;
            const cached = this.actorDbCache[actorName];
            if (cached && (now - cached.cachedAt) < 5000) {
                face.db_record = cached.record;
                continue;
            }

            try {
                const res = await fetch(`/api/actors/lookup?name=${encodeURIComponent(actorName)}`);
                if (res.ok) {
                    const data = await res.json();
                    const record = (data.found && data.actor) ? data.actor : null;
                    this.actorDbCache[actorName] = { record, cachedAt: now };
                    face.db_record = record;
                } else {
                    this.actorDbCache[actorName] = { record: null, cachedAt: now };
                }
            } catch (e) {
                this.actorDbCache[actorName] = { record: null, cachedAt: now };
            }
        }
    },

    /**
     * Render Face Bounding Boxes on Overlay Canvas (Viewfinder Superimposition)
     * Handles CSS object-fit: cover scaling projection accurately.
     */
    renderBoundingBoxes(faces, nativeDimensions) {
        if (!this.detectionCanvas || !this.detectionCtx) return;

        const canvas = this.detectionCanvas;
        const ctx = this.detectionCtx;

        // Obtain displayed container dimensions
        const displayWidth = canvas.clientWidth;
        const displayHeight = canvas.clientHeight;

        if (!displayWidth || !displayHeight) return;

        // Resize canvas drawing buffer to match CSS display pixel size
        if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
            canvas.width = displayWidth;
            canvas.height = displayHeight;
        }

        // Clear previous frame bounding boxes
        ctx.clearRect(0, 0, displayWidth, displayHeight);

        // If no faces detected, canvas remains clear
        if (!faces || faces.length === 0) {
            return;
        }

        // Compute aspect ratio projection scaling (matches CSS object-fit: cover)
        const nativeW = nativeDimensions ? nativeDimensions[0] : (this.latestFrame.width || 1280);
        const nativeH = nativeDimensions ? nativeDimensions[1] : (this.latestFrame.height || 720);

        const scale = Math.max(displayWidth / nativeW, displayHeight / nativeH);
        const offsetX = (displayWidth - nativeW * scale) / 2;
        const offsetY = (displayHeight - nativeH * scale) / 2;

        // Render each detected face bounding box
        faces.forEach((face, index) => {
            const [x1, y1, x2, y2] = face.bbox;
            const confidence = face.confidence;

            // Project coordinates to display space
            let boxX = Math.round(x1 * scale + offsetX);
            const boxY = Math.round(y1 * scale + offsetY);
            const boxW = Math.round((x2 - x1) * scale);
            const boxH = Math.round((y2 - y1) * scale);

            // If front camera, mirror the X coordinate so it aligns with the CSS-mirrored video
            if (this.activeFacingMode === 'user') {
                boxX = displayWidth - (boxX + boxW);
            }

            // Styling based on recognition status
            const isKnown = face.status === 'known';
            const isUnknown = face.status === 'unknown';
            const primaryColor = isKnown ? '#00FF66' : (isUnknown ? '#FF7D00' : '#00E5FF');
            const cornerColor = isKnown ? '#00FF66' : (isUnknown ? '#FF7D00' : '#00FF66');
            const fillColor = isKnown ? 'rgba(0, 255, 102, 0.08)' : (isUnknown ? 'rgba(255, 125, 0, 0.08)' : 'rgba(0, 229, 255, 0.08)');

            // 1. Semi-transparent subtle tint inside bounding box
            ctx.fillStyle = fillColor;
            ctx.fillRect(boxX, boxY, boxW, boxH);

            // 2. Primary bounding box border
            ctx.strokeStyle = primaryColor;
            ctx.lineWidth = 2;
            ctx.strokeRect(boxX, boxY, boxW, boxH);

            // 3. High-tech corner brackets (AI reticle accent)
            const cornerLen = Math.min(16, Math.floor(Math.min(boxW, boxH) * 0.25));
            ctx.strokeStyle = cornerColor;
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';

            // Top-Left corner
            ctx.beginPath();
            ctx.moveTo(boxX, boxY + cornerLen);
            ctx.lineTo(boxX, boxY);
            ctx.lineTo(boxX + cornerLen, boxY);
            ctx.stroke();

            // Top-Right corner
            ctx.beginPath();
            ctx.moveTo(boxX + boxW - cornerLen, boxY);
            ctx.lineTo(boxX + boxW, boxY);
            ctx.lineTo(boxX + boxW, boxY + cornerLen);
            ctx.stroke();

            // Bottom-Left corner
            ctx.beginPath();
            ctx.moveTo(boxX, boxY + boxH - cornerLen);
            ctx.lineTo(boxX, boxY + boxH);
            ctx.lineTo(boxX + cornerLen, boxY + boxH);
            ctx.stroke();

            // Bottom-Right corner
            ctx.beginPath();
            ctx.moveTo(boxX + boxW - cornerLen, boxY + boxH);
            ctx.lineTo(boxX + boxW, boxY + boxH);
            ctx.lineTo(boxX + boxW, boxY + boxH - cornerLen);
            ctx.stroke();

            // Recognition Label Pill above bounding box
            let labelText = '';
            if (face.actor && typeof face.distance === 'number') {
                const distStr = face.distance < 900 ? face.distance.toFixed(2) : '-';
                const actorDisplay = (isUnknown || face.actor === 'Tidak Dikenali') ? 'Unknown' : face.actor;
                labelText = `${actorDisplay} · ${distStr}`;
            } else {
                const confPercent = Math.round(confidence * 100);
                labelText = `Face ${confPercent}%`;
            }

            ctx.font = '600 11px "Inter", -apple-system, BlinkMacSystemFont, sans-serif';
            const textMetrics = ctx.measureText(labelText);
            const badgeW = textMetrics.width + 16;
            const badgeH = 20;
            const badgeX = boxX;
            const badgeY = Math.max(4, boxY - badgeH - 4);

            // Badge background pill
            ctx.fillStyle = 'rgba(5, 7, 14, 0.9)';
            ctx.beginPath();
            ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
            ctx.fill();

            // Badge border
            ctx.strokeStyle = isKnown ? 'rgba(0, 255, 102, 0.6)' : (isUnknown ? 'rgba(255, 125, 0, 0.6)' : 'rgba(0, 229, 255, 0.5)');
            ctx.lineWidth = 1;
            ctx.stroke();

            // Status indicator dot
            ctx.fillStyle = isKnown ? '#00FF66' : (isUnknown ? '#FF7D00' : '#00E5FF');
            ctx.beginPath();
            ctx.arc(badgeX + 7, badgeY + badgeH / 2, 2.5, 0, Math.PI * 2);
            ctx.fill();

            // Text label
            ctx.fillStyle = '#FFFFFF';
            ctx.fillText(labelText, badgeX + 14, badgeY + badgeH - 5.5);
        });
    },

    /**
     * Update YOLO, FaceNet, and Recognition Telemetry in UI
     */
    updateYoloTelemetry(facesCount, inferenceMs, facenetMs = 0, faces = []) {
        const countEl = this.elements.statFacesCount;
        const latencyEl = this.elements.statYoloLatency;
        const facenetLatencyEl = this.elements.statFaceNetLatency;

        if (countEl) {
            countEl.textContent = facesCount === 1 ? '1 Face' : `${facesCount} Faces`;
            countEl.classList.toggle('active', facesCount > 0);
        }

        if (latencyEl) {
            latencyEl.textContent = `${Math.round(inferenceMs)} ms`;
        }

        if (facenetLatencyEl) {
            facenetLatencyEl.textContent = `${Math.round(facenetMs)} ms`;
        }

        this.renderDetectedFacesList(faces);
    },

    renderDetectedFacesList(faces = []) {
        const listEl = document.getElementById('detectedFacesList');
        const emptyEl = document.getElementById('emptyFacesNote');
        if (!listEl) return;

        if (!faces || faces.length === 0) {
            if (emptyEl) emptyEl.style.display = 'flex';
            listEl.innerHTML = '';
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        let html = '';
        faces.forEach((face) => {
            const isKnown = face.status === 'known';
            const rawActor = face.actor || (face.db_record ? face.db_record.full_name : null);
            const actorName = (isKnown && rawActor && rawActor !== 'Tidak Dikenali') ? rawActor : 'Unknown Person';
            const distStr = typeof face.distance === 'number' && face.distance < 900 ? face.distance.toFixed(3) : '-';
            const actorUuid = face.db_record ? face.db_record.uuid : null;
            const charName = face.db_record ? face.db_record.current_character_name : null;

            html += `
                <div class="detected-face-card ${isKnown ? 'is-known' : 'is-unknown'}">
                    <div class="face-card-header">
                        <span class="face-badge ${isKnown ? 'badge-known' : 'badge-unknown'}">
                            ${isKnown ? 'KNOWN' : 'UNKNOWN'}
                        </span>
                        <span class="face-dist">Dist: ${distStr}</span>
                    </div>
                    <div class="face-card-body">
                        <strong class="face-name">${this.escapeHtml(actorName)}</strong>
                        ${charName ? `<span class="face-role">Role: ${this.escapeHtml(charName)}</span>` : ''}
                    </div>
                    ${actorUuid ? `
                        <a href="/actors/${actorUuid}" class="face-card-link">
                            <span>Open Profile</span>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </a>
                    ` : ''}
                </div>
            `;
        });

        listEl.innerHTML = html;
    },

    /**
     * Pause / Stop Continuous Pipeline Ingestion (Without stopping camera stream)
     */
    stopPipeline() {
        if (this.pipelineIntervalId) {
            clearInterval(this.pipelineIntervalId);
            this.pipelineIntervalId = null;
        }

        this.isPipelineActive = false;
        this.isDetectionInFlight = false;
        this.latestFrame.status = 'IDLE';

        // Clear bounding boxes on detection canvas
        if (this.detectionCanvas && this.detectionCtx) {
            this.detectionCtx.clearRect(0, 0, this.detectionCanvas.width, this.detectionCanvas.height);
        }

        this.latestDetections = [];
        this.facesDetectedCount = 0;
        this.facenetProcessedCount = 0;
        this.updateYoloTelemetry(0, 0, 0, []);
        this.renderDetectedFacesList([]);

        // Reset video state
        this.prevFrameData = null;
        this.consecutiveStableFrames = 0;
        this.setVideoState('idle');
        if (this.elements.videoStatePill) this.elements.videoStatePill.style.display = 'none';

        if (this.isStreaming) {
            this.updateStatus('active', 'Camera Active');
        }
    },

    /**
     * Temporary pause when browser tab is hidden
     */
    pausePipelineForVisibility() {
        if (this.pipelineIntervalId) {
            clearInterval(this.pipelineIntervalId);
            this.pipelineIntervalId = null;
        }
        this.isPipelineActive = false;
        this.isDetectionInFlight = false;
    },

    /**
     * Toggle Pipeline Ingestion between Active and Paused
     */
    togglePipeline() {
        if (!this.isStreaming) return;

        if (this.isPipelineActive) {
            this.stopPipeline();
        } else {
            this.startPipeline();
        }
    },

    /**
     * Stop Camera Stream and Clean Up All Resources
     */
    stopCamera() {
        // 1. Stop continuous frame acquisition & detection pipeline
        this.stopPipeline();

        // 2. Stop all camera tracks cleanly
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => {
                track.stop();
            });
            this.mediaStream = null;
        }

        // 3. Reset Video & Detection Canvas
        const video = this.elements.video;
        if (video) {
            video.pause();
            video.srcObject = null;
            video.style.display = 'none';
        }

        if (this.detectionCanvas) {
            if (this.detectionCtx) {
                this.detectionCtx.clearRect(0, 0, this.detectionCanvas.width, this.detectionCanvas.height);
            }
            this.detectionCanvas.style.display = 'none';
        }

        this.isStreaming = false;
        this.latestFrame.status = 'IDLE';

        // 4. Reset UI Elements
        if (this.elements.placeholder) this.elements.placeholder.style.display = 'flex';
        if (this.elements.overlay) this.elements.overlay.style.display = 'none';
        if (this.elements.overlayPill) this.elements.overlayPill.style.display = 'none';

        if (this.elements.btnSwitch) this.elements.btnSwitch.disabled = true;
        if (this.elements.btnCapture) this.elements.btnCapture.disabled = true;

        // Remove mirror transform when camera stops
        if (this.elements.video) this.elements.video.style.transform = '';
        if (this.detectionCanvas) this.detectionCanvas.style.transform = '';

        if (this.elements.btnToggle) {
            this.elements.btnToggle.classList.remove('btn-stop');
            this.elements.btnToggle.classList.add('btn-start');
            if (this.elements.btnToggleText) this.elements.btnToggleText.textContent = 'Start Camera';
        }

        this.updateStatus('idle', 'Standby');
        this.updateYoloTelemetry(0, 0, 0, []);

        if (this.elements.videoStatePill) this.elements.videoStatePill.style.display = 'none';
        this.hidePauseActionOverlay();

        this.syncActiveActors([]);
    },

    /**
     * Switch / Flip Camera between Rear and Front
     */
    async switchCamera() {
        if (!this.isStreaming) return;
        this.currentFacingMode = this.currentFacingMode === 'environment' ? 'user' : 'environment';
        this.stopCamera();
        await this.startCamera();
    },

    /**
     * Manual Snapshot Capture into Preview Card
     * Satisfies: "Manual Capture Frame still works"
     */
    captureManualSnapshot() {
        if (!this.isStreaming) return;

        const video = this.elements.video;
        if (!video || video.readyState < 2) return;

        const width = video.videoWidth;
        const height = video.videoHeight;
        if (!width || !height) return;

        // Use dedicated snapshot canvas
        const snapCanvas = this.elements.canvas || document.createElement('canvas');
        snapCanvas.width = width;
        snapCanvas.height = height;

        const snapCtx = snapCanvas.getContext('2d');
        
        // If front camera, flip the snapshot so it matches what the user saw in the mirrored preview
        if (this.activeFacingMode === 'user') {
            snapCtx.translate(width, 0);
            snapCtx.scale(-1, 1);
        }
        
        snapCtx.drawImage(video, 0, 0, width, height);

        snapCanvas.toBlob((blob) => {
            if (!blob) return;
            this.totalManualSnapshots++;

            const dataUrl = snapCanvas.toDataURL('image/jpeg', 0.9);
            this.displayCapturedFrame({
                dataUrl: dataUrl,
                width: width,
                height: height,
                sizeBytes: blob.size,
                timestamp: new Date(),
                snapshotNumber: this.totalManualSnapshots
            });
        }, 'image/jpeg', 0.9);
    },

    /**
     * Display Captured Frame Preview and Metadata
     */
    displayCapturedFrame({ dataUrl, width, height, sizeBytes, snapshotNumber }) {
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = `indolens-snapshot-${snapshotNumber}.jpg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        const kbSize = (sizeBytes / 1024).toFixed(1);
        this.showToast(`Snapshot #${snapshotNumber} saved (${width}x${height}, ${kbSize} KB)`);
    },

    showToast(message) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = 'background:#0B0F19;color:#FFFFFF;border:1px solid #165DFF;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 8px 24px rgba(0,0,0,0.4);margin-top:8px;';
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    },

    /**
     * Get the Latest Frame Buffer (Public API for future AI pipeline sessions)
     */
    getLatestFrame() {
        if (!this.isStreaming || !this.latestFrame.frameNumber) {
            return null;
        }

        return {
            frameNumber: this.latestFrame.frameNumber,
            timestamp: this.latestFrame.timestamp,
            captureTime: this.latestFrame.captureTime || performance.now(),
            width: this.latestFrame.width,
            height: this.latestFrame.height,
            status: this.latestFrame.status,
            canvas: this.latestFrame.canvas,
            // Lazy extractors:
            getImageData: () => {
                return this.bufferCtx.getImageData(0, 0, this.latestFrame.width, this.latestFrame.height);
            },
            getBlob: (quality = 0.85) => {
                return new Promise((resolve) => {
                    this.bufferCanvas.toBlob(resolve, 'image/jpeg', quality);
                });
            }
        };
    },

    /**
     * Check if Pipeline is Ready
     */
    isPipelineReady() {
        return this.isStreaming && this.isPipelineActive && this.latestFrame.frameNumber > 0;
    },

    /**
     * Handle Camera Permissions & Access Errors
     */
    handleCameraError(error) {
        let msg = 'Failed to access camera.';

        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            msg = 'Camera access was denied. Please allow camera access in your browser or device settings.';
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            msg = 'No camera found on this device.';
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            msg = 'Camera is already in use by another application or tab.';
        } else if (error.name === 'OverconstrainedError') {
            msg = 'Requested camera resolution is not supported by your camera hardware.';
        } else if (error.name === 'SecurityError') {
            msg = 'Camera access requires a secure origin (HTTPS or localhost).';
        } else {
            msg = `Camera error: ${error.message || error.name}`;
        }

        this.showError(msg);
        this.updateStatus('error', 'Camera Error');
    },

    showError(msg) {
        if (this.elements.errorMessage) this.elements.errorMessage.textContent = msg;
        if (this.elements.errorBanner) this.elements.errorBanner.style.display = 'flex';
    },

    hideError() {
        if (this.elements.errorBanner) this.elements.errorBanner.style.display = 'none';
    },

    /**
     * Update Status Badge & Telemetry
     */
    updateStatus(state, label) {
        const badge = this.elements.statusBadge;
        const text = this.elements.statusText;

        if (text) text.textContent = label;

        if (badge) {
            badge.classList.remove('active', 'streaming', 'error');
            if (state === 'active') badge.classList.add('active');
            if (state === 'streaming') badge.classList.add('streaming');
            if (state === 'error') badge.classList.add('error');
        }
    }
};

/**
 * Public IndoLens Pipeline Interface
 * Accessible globally via window.IndoLensPipeline
 */
window.IndoLensPipeline = {
    getLatestFrame: () => CameraCapture.getLatestFrame(),
    getLatestDetections: () => CameraCapture.latestDetections,
    getFacesCount: () => CameraCapture.facesDetectedCount,
    isReady: () => CameraCapture.isPipelineReady(),
    start: () => CameraCapture.startPipeline(),
    stop: () => CameraCapture.stopPipeline(),
};

// Auto-initialize when DOM is ready or immediately if already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        CameraCapture.init();
    });
} else {
    CameraCapture.init();
}

