/**
 * IndoLens - Real-Time YOLO Face Detection & Actor Recognition Module (Session 5)
 * Integrates real-time camera frames with Ultralytics YOLOv8 face detection,
 * FaceNet InceptionResnetV1 128-D embeddings, and Euclidean distance threshold matching (0.65).
 * Renders recognized actor names, Euclidean distances, and Known/Unknown reticles.
 *
 * Session 7: Video Running vs Pause — Frame-Difference State Detection
 * Detects whether the captured external video is changing (running) or stable (paused)
 * using lightweight pixel-level frame differencing on the existing yoloCanvas.
 */

const CameraCapture = {
    // Media Stream State
    mediaStream: null,
    currentFacingMode: 'environment', // 'environment' (rear camera) by default for phone-to-screen pointing
    activeFacingMode: 'environment',  // Actual facing mode active on track
    isStreaming: false,

    // Real-Time Frame Pipeline State (Session 2)
    isPipelineActive: false,
    pipelineIntervalId: null,
    pipelineTargetFps: 10,           // Controlled acquisition rate: 10 FPS (100ms interval)
    pipelineStartTime: null,
    totalFramesIngested: 0,
    totalManualSnapshots: 0,

    // Reusable Buffer Canvas (O(1) memory allocation - prevents GC pressure)
    bufferCanvas: null,
    bufferCtx: null,

    // Dedicated downsampled canvas for YOLO inference input.
    // Viewfinder stays at native res; YOLO receives a smaller copy for fast transfer.
    yoloCanvas: null,
    yoloCtx: null,
    YOLO_SEND_MAX_WIDTH: 640, // Max pixel width sent to Python YOLO service

    // Real-Time YOLO Face Detection & FaceNet State (Session 4)
    detectionCanvas: null,
    detectionCtx: null,
    isDetectionInFlight: false,
    latestDetections: [],
    facesDetectedCount: 0,
    lastYoloInferenceMs: 0,
    lastFaceNetLatencyMs: 0,
    facenetProcessedCount: 0,
    actorDbCache: {}, // Session 6: Cache for resolved MySQL actor records
    lastActiveSyncTime: 0, // Session 9: Throttling for /api/actors/active sync

    // Session 7: Video State Detection (Frame Difference)
    videoState: 'idle',                    // 'idle' | 'running' | 'paused'
    prevFrameData: null,                   // Previous frame's pixel data (reusable buffer)
    consecutiveStableFrames: 0,            // Counter for consecutive stable frames
    PAUSE_DIFF_THRESHOLD: 3.2,             // Mean pixel difference threshold for pause detection (tuned for handheld stability)
    PAUSE_CONSECUTIVE_REQUIRED: 4,         // Consecutive stable frames required (~1.2s at 3 FPS)

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
            // Viewfinder & Video
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

            // Badges & Buttons
            statusBadge: document.getElementById('cameraStatusBadge'),
            statusText: document.getElementById('cameraStatusText'),
            btnToggle: document.getElementById('btnToggleCamera'),
            btnToggleText: document.getElementById('btnToggleText'),
            btnSwitch: document.getElementById('btnSwitchCamera'),
            btnCapture: document.getElementById('btnCaptureFrame'),
            btnStartPrompt: document.getElementById('btnStartPrompt'),

            // Telemetry Fields
            statStreamStatus: document.getElementById('statStreamStatus'),
            statPipelineStage: document.getElementById('statPipelineStage'),
            statFacesCount: document.getElementById('statFacesCount'),
            statRecognitionStatus: document.getElementById('statRecognitionStatus'),
            statFaceNetStatus: document.getElementById('statFaceNetStatus'),
            statYoloLatency: document.getElementById('statYoloLatency'),
            statFaceNetLatency: document.getElementById('statFaceNetLatency'),
            statCameraDevice: document.getElementById('statCameraDevice'),
            statResolution: document.getElementById('statResolution'),
            statFramesCaptured: document.getElementById('statFramesCaptured'),
            statCaptureRate: document.getElementById('statCaptureRate'),
            statFrameBuffer: document.getElementById('statFrameBuffer'),

            // Captured Frame Preview
            capturedImagePreview: document.getElementById('capturedImagePreview'),
            capturedPlaceholder: document.getElementById('capturedPlaceholder'),
            capturedFrameTag: document.getElementById('capturedFrameTag'),
            capturedMeta: document.getElementById('capturedMeta'),
            metaTimestamp: document.getElementById('metaTimestamp'),
            metaDimensions: document.getElementById('metaDimensions'),
            metaFormat: document.getElementById('metaFormat'),

            // Session 7: Video State elements
            videoStatePill: document.getElementById('videoStatePill'),
            videoStateIcon: document.getElementById('videoStateIcon'),
            videoStateText: document.getElementById('videoStateText'),
            pauseActionOverlay: document.getElementById('pauseActionOverlay'),
            statVideoState: document.getElementById('statVideoState'),
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

        // Update stream telemetry
        if (this.elements.statStreamStatus) this.elements.statStreamStatus.textContent = 'Active (Live)';
        if (this.elements.statCameraDevice) this.elements.statCameraDevice.textContent = deviceLabel;
        if (this.elements.statResolution) this.elements.statResolution.textContent = `${width} × ${height} px`;
        if (this.elements.overlayResolution) this.elements.overlayResolution.textContent = `${width} × ${height}`;
        if (this.elements.overlayFacingMode) {
            this.elements.overlayFacingMode.textContent = activeFacing === 'user' ? 'Front (User)' : 'Rear (Environment)';
        }

        // AUTOMATICALLY START CONTINUOUS REAL-TIME FRAME PIPELINE & YOLO DETECTION
        this.startPipeline();
    },

    /**
     * Start Real-Time Continuous Frame Acquisition & YOLO Detection Loop
     */
    startPipeline() {
        if (!this.isStreaming || this.isPipelineActive) return;

        this.isPipelineActive = true;
        this.pipelineStartTime = performance.now();
        this.totalFramesIngested = 0;
        this.isDetectionInFlight = false;

        // Session 7: Reset frame-difference state on pipeline start
        this.prevFrameData = null;
        this.consecutiveStableFrames = 0;
        this.setVideoState('idle');

        // Update telemetry for active pipeline
        this.updateStatus('streaming', 'Pipeline Active');
        this.setPipelineStage('RECOGNITION ACTIVE', true);

        // Session 7: Show video state pill
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

        // Session 7: Frame-Difference State Detection (reuses yoloCanvas)
        this.computeFrameDifference(yoloW, yoloH);

        // 2. Update Latest Frame Buffer State (In-place O(1) update)
        this.totalFramesIngested++;
        this.latestFrame.frameNumber = this.totalFramesIngested;
        this.latestFrame.timestamp = Date.now();
        this.latestFrame.captureTime = performance.now();
        this.latestFrame.width = width;
        this.latestFrame.height = height;
        this.latestFrame.status = 'READY_FOR_YOLO';

        // 3. Update Real-Time Telemetry
        if (this.elements.statFramesCaptured) {
            this.elements.statFramesCaptured.textContent = String(this.totalFramesIngested);
        }

        if (this.elements.statFrameBuffer) {
            this.elements.statFrameBuffer.textContent = `${width} × ${height} px · Frame #${this.totalFramesIngested} (Ready)`;
        }

        // Calculate live acquisition rate (FPS)
        const elapsedSeconds = (performance.now() - this.pipelineStartTime) / 1000;
        if (elapsedSeconds > 0.5) {
            const currentFps = (this.totalFramesIngested / elapsedSeconds).toFixed(1);
            if (this.elements.statCaptureRate) {
                this.elements.statCaptureRate.textContent = `${currentFps} FPS`;
            }
        }

        // 4. DISPATCH FRAME TO YOLO FACE DETECTION (Session 3 & 7)
        // Set the latest frame as pending, explicitly discarding any stale pending frames
        const newFrame = this.getLatestFrame();
        if (this.isDetectionInFlight && this.pendingYoloFrame) {
            console.log(`[Latest-Frame-Wins] DISCARD Frame #${this.pendingYoloFrame.frameNumber} in favor of Frame #${newFrame.frameNumber}`);
        }
        this.pendingYoloFrame = newFrame;

        if (!this.isDetectionInFlight) {
            this.triggerYoloDetection();
        }
    },

    /**
     * Session 7: Lightweight Frame-Difference Computation
     * Compares current yoloCanvas pixels against stored previous frame.
     * Uses strided RGB sampling for sub-millisecond performance.
     * Determines 'running' vs 'paused' video state.
     */
    computeFrameDifference(yoloW, yoloH) {
        const currentImageData = this.yoloCtx.getImageData(0, 0, yoloW, yoloH);
        const currentData = currentImageData.data; // Uint8ClampedArray (RGBA)

        if (!this.prevFrameData || this.prevFrameData.length !== currentData.length) {
            // First frame or resolution changed — allocate buffer once and mark as running
            this.prevFrameData = new Uint8ClampedArray(currentData.length);
            this.prevFrameData.set(currentData);
            this.consecutiveStableFrames = 0;
            if (this.videoState === 'idle') {
                this.setVideoState('running');
            }
            return;
        }

        // Fast strided sampling: sample every 8th pixel for speed (<0.3ms on mobile)
        const stride = 8 * 4; // 8 pixels × 4 channels (RGBA)
        let totalDiff = 0;
        let sampleCount = 0;

        for (let i = 0; i < currentData.length; i += stride) {
            // Compare RGB only (skip alpha channel at i+3)
            totalDiff += Math.abs(currentData[i] - this.prevFrameData[i]);       // R
            totalDiff += Math.abs(currentData[i + 1] - this.prevFrameData[i + 1]); // G
            totalDiff += Math.abs(currentData[i + 2] - this.prevFrameData[i + 2]); // B
            sampleCount += 3;
        }

        const meanDiff = sampleCount > 0 ? totalDiff / sampleCount : 0;

        // Session 7: Diagnostic logging for pause detection tuning
        if (this.totalFramesIngested % 5 === 0) {
            console.log(`[Diagnostic] Video State: ${this.videoState} | Consecutive: ${this.consecutiveStableFrames} | Mean Diff: ${meanDiff.toFixed(3)}`);
        }

        // Store current frame as previous for next comparison (O(1) memory buffer reuse)
        this.prevFrameData.set(currentData);

        // State determination
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
     * Session 7: Set Video State and Update All Related UI
     * Manages state pill, telemetry field, and pause action overlay.
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
                // idle
                if (this.elements.videoStateIcon) this.elements.videoStateIcon.textContent = '▶';
                if (this.elements.videoStateText) this.elements.videoStateText.textContent = 'Idle';
            }
        }

        // Update Telemetry Video State field
        const statEl = this.elements.statVideoState;
        if (statEl) {
            statEl.classList.remove('state-running', 'state-paused');

            if (state === 'running') {
                statEl.textContent = 'Running';
                statEl.classList.add('state-running');
            } else if (state === 'paused') {
                statEl.textContent = 'Paused';
                statEl.classList.add('state-paused');
            } else {
                statEl.textContent = 'Idle';
            }
        }

        // Manage Pause Action Overlay
        if (state === 'paused') {
            this.showPauseActionOverlay();
        } else {
            this.hidePauseActionOverlay();
        }
    },

    /**
     * Session 7 & 9: Show Pause Action Overlay for Recognized Known Actors
     * Supports multiple detected faces independently. Only displays for faces with status === 'known' AND db_record.id exists.
     * Records/synchronizes recognized identities with MySQL database via /api/actors/active.
     */
    showPauseActionOverlay() {
        const overlay = this.elements.pauseActionOverlay;
        if (!overlay) return;

        // Find all known faces with database records
        const knownWithRecords = (this.latestDetections || []).filter(
            f => f.status === 'known' && f.db_record && f.db_record.id
        );

        if (knownWithRecords.length === 0) {
            // No known actor with db record — hide overlay
            overlay.style.display = 'none';
            overlay.innerHTML = '';
            return;
        }

        // Deduplicate multiple bounding boxes of the same actor
        const seenActorIds = new Set();
        const uniqueKnownFaces = [];
        for (const face of knownWithRecords) {
            if (!seenActorIds.has(face.db_record.id)) {
                seenActorIds.add(face.db_record.id);
                uniqueKnownFaces.push(face);
            }
        }

        let html = '';
        for (const known of uniqueKnownFaces) {
            const actorName = known.actor || known.db_record.full_name || 'Unknown Actor';
            const actorId = known.db_record.id;
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
                    <a href="/actors/${actorId}" class="pause-action-btn">
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

        // Session 9: Synchronize paused recognized identities to MySQL database
        const activeNames = uniqueKnownFaces.map(f => f.db_record.full_name || f.actor);
        this.syncActiveActors(activeNames);
    },

    /**
     * Session 9: Synchronize recognized active actor identities to Laravel MySQL backend.
     * Updates actors.is_detected in database so Actor List and Actor Detail reflect detection state.
     * Strict rule: Never sends unknown or fabricated identities.
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
     * Session 7: Hide and Clear Pause Action Overlay
     */
    hidePauseActionOverlay() {
        const overlay = this.elements.pauseActionOverlay;
        if (overlay) {
            overlay.style.display = 'none';
            overlay.innerHTML = '';
        }
    },

    /**
     * Session 7: HTML Escape utility to prevent XSS in actor names
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
        console.log(`[Latest-Frame-Wins] Frame #${frame.frameNumber} -> PROCESSING`);

        const t_capture = frame.captureTime || performance.now();
        const t_jpeg_start = performance.now();

        try {
            // Use the downsampled YOLO canvas blob
            // Lower quality to 0.70 for ultra-fast mobile encoding (virtually no impact on YOLOv8)
            const blob = await new Promise((resolve) =>
                this.yoloCanvas.toBlob(resolve, 'image/jpeg', 0.70)
            );
            const t_jpeg_ready = performance.now();

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
            const t_rec_complete = performance.now();

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

                // Session 6: Resolve recognized known actor against MySQL database record
                const t_db_start = performance.now();
                await this.resolveKnownActors(this.latestDetections);
                const t_db_resolve = performance.now();

                // Render bounding boxes over live viewfinder
                this.renderBoundingBoxes(this.latestDetections, data.frame_dimensions);
                const t_rendered = performance.now();

                // Complete pipeline telemetry instrumentation (Capture -> Render)
                const visibleLatency = Math.round(t_rendered - t_capture);
                console.log(`[Pipeline Latency] Frame #${frame.frameNumber} Visible: ${visibleLatency}ms | Breakdown:
  Frame captured -> JPEG ready : ${(t_jpeg_ready - t_capture).toFixed(1)} ms (toBlob: ${(t_jpeg_ready - t_jpeg_start).toFixed(1)} ms)
  Request sent -> YOLO response: ${(t_yolo_resp - t_req_sent).toFixed(1)} ms
    └ Server YOLO Inference    : ${data.yolo_time_ms ?? '-'} ms
    └ Server FaceNet Complete  : ${data.facenet_time_ms ?? '-'} ms
    └ Server Recognition Match : ${data.recognition_time_ms ?? '-'} ms
  DB Resolve complete          : ${(t_db_resolve - t_db_start).toFixed(1)} ms
  Overlay rendered             : ${(t_rendered - t_db_resolve).toFixed(1)} ms
  Actual Visible Latency (Capture -> Render): ${visibleLatency} ms`);

                // Session 7: If currently paused, refresh overlay with latest detections
                if (this.videoState === 'paused') {
                    this.showPauseActionOverlay();
                } else {
                    // Session 9: Periodically sync recognized known actors during live streaming (throttled to ~1.5s)
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

            // Immediately process the newest pending frame if available (Latest-Frame-Wins)
            if (this.pendingYoloFrame) {
                this.triggerYoloDetection();
            }
        }
    },

    /**
     * Session 6: Resolve recognized actor against Laravel MySQL database.
     * Enriches recognized known faces with real database actor record.
     * Strict rule: When face.status === 'unknown', NO lookup is performed.
     */
    async resolveKnownActors(faces) {
        if (!faces || faces.length === 0) return;

        const knownFaces = faces.filter(f => f.status === 'known' && f.actor && f.actor !== 'Unknown');

        if (knownFaces.length === 0) return;

        for (const face of knownFaces) {
            const actorName = face.actor;
            if (this.actorDbCache[actorName] !== undefined) {
                face.db_record = this.actorDbCache[actorName];
                continue;
            }

            try {
                const res = await fetch(`/api/actors/lookup?name=${encodeURIComponent(actorName)}`);
                if (res.ok) {
                    const data = await res.json();
                    const record = (data.found && data.actor) ? data.actor : null;
                    this.actorDbCache[actorName] = record;
                    face.db_record = record;
                } else {
                    this.actorDbCache[actorName] = null;
                }
            } catch (e) {
                this.actorDbCache[actorName] = null;
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

            // Styling based on recognition status (Session 5: Known vs Unknown)
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

            // 4. Recognition Badge Pill above bounding box (Session 5 & 7: Actor Name & Euclidean Distance in English)
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
        const recEl = this.elements.statRecognitionStatus;
        const facenetStatusEl = this.elements.statFaceNetStatus;
        const facenetLatencyEl = this.elements.statFaceNetLatency;

        if (countEl) {
            countEl.textContent = facesCount === 1 ? '1 Face' : `${facesCount} Faces`;
            if (facesCount > 0) {
                countEl.classList.add('active');
            } else {
                countEl.classList.remove('active');
            }
        }

        if (latencyEl) {
            latencyEl.textContent = `${Math.round(inferenceMs)} ms`;
        }

        // Recognition status update
        if (recEl) {
            recEl.classList.remove('known', 'unknown');
            if (facesCount > 0) {
                const knownFaces = (faces || []).filter(f => f.status === 'known');
                const unknownFaces = (faces || []).filter(f => f.status === 'unknown');

                if (knownFaces.length > 0 && unknownFaces.length === 0) {
                    recEl.textContent = knownFaces.length === 1 ? knownFaces[0].actor : `${knownFaces.length} Known`;
                    recEl.classList.add('known');
                } else if (knownFaces.length === 0 && unknownFaces.length > 0) {
                    recEl.textContent = unknownFaces.length === 1 ? '1 Unknown' : `${unknownFaces.length} Unknown`;
                    recEl.classList.add('unknown');
                } else if (knownFaces.length > 0 && unknownFaces.length > 0) {
                    recEl.textContent = `${knownFaces.length} Known, ${unknownFaces.length} Unknown`;
                    recEl.classList.add('known');
                } else {
                    recEl.textContent = 'Processing...';
                }
            } else {
                recEl.textContent = 'Standby (No Face)';
            }
        }

        if (facenetStatusEl) {
            if (facesCount > 0) {
                const validEmbs = (faces || []).filter(f => f.embedding_dim === 128).length;
                facenetStatusEl.textContent = validEmbs === 1 ? '1 Face · 128-D (OK)' : `${validEmbs} Faces · 128-D (OK)`;
                facenetStatusEl.classList.add('active');
            } else {
                facenetStatusEl.textContent = 'Standby (No Face)';
                facenetStatusEl.classList.remove('active');
            }
        }

        if (facenetLatencyEl) {
            facenetLatencyEl.textContent = `${Math.round(facenetMs)} ms`;
        }
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

        // Session 7: Reset video state
        this.prevFrameData = null;
        this.consecutiveStableFrames = 0;
        this.setVideoState('idle');
        if (this.elements.videoStatePill) this.elements.videoStatePill.style.display = 'none';

        if (this.isStreaming) {
            this.updateStatus('active', 'Camera Active');
            this.setPipelineStage('PAUSED', false);
        } else {
            this.setPipelineStage('STANDBY', false);
        }

        if (this.elements.statCaptureRate) {
            this.elements.statCaptureRate.textContent = '0 FPS';
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

        // 5. Reset Telemetry
        this.updateStatus('idle', 'Camera Standby');
        this.setPipelineStage('STANDBY', false);
        this.updateYoloTelemetry(0, 0, 0, []);
        if (this.elements.statStreamStatus) this.elements.statStreamStatus.textContent = 'Standby';
        if (this.elements.statRecognitionStatus) {
            this.elements.statRecognitionStatus.textContent = 'Standby';
            this.elements.statRecognitionStatus.classList.remove('known', 'unknown');
        }
        if (this.elements.statCameraDevice) this.elements.statCameraDevice.textContent = 'None';
        if (this.elements.statResolution) this.elements.statResolution.textContent = '-';
        if (this.elements.statCaptureRate) this.elements.statCaptureRate.textContent = '0 FPS';
        if (this.elements.statFrameBuffer) this.elements.statFrameBuffer.textContent = '-';

        // Session 7: Ensure video state pill and overlay are hidden
        if (this.elements.videoStatePill) this.elements.videoStatePill.style.display = 'none';
        this.hidePauseActionOverlay();

        // Session 9: Reset active detection status in backend on camera stop
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
    displayCapturedFrame({ dataUrl, width, height, sizeBytes, timestamp, snapshotNumber }) {
        if (this.elements.capturedPlaceholder) {
            this.elements.capturedPlaceholder.style.display = 'none';
        }

        if (this.elements.capturedImagePreview) {
            this.elements.capturedImagePreview.src = dataUrl;
            this.elements.capturedImagePreview.style.display = 'block';
        }

        if (this.elements.capturedFrameTag) {
            this.elements.capturedFrameTag.textContent = `Snapshot #${snapshotNumber}`;
        }

        if (this.elements.capturedMeta) {
            this.elements.capturedMeta.style.display = 'flex';
        }

        const formattedTime = timestamp.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });

        const kbSize = (sizeBytes / 1024).toFixed(1);

        if (this.elements.metaTimestamp) this.elements.metaTimestamp.textContent = formattedTime;
        if (this.elements.metaDimensions) this.elements.metaDimensions.textContent = `${width} × ${height} px`;
        if (this.elements.metaFormat) this.elements.metaFormat.textContent = `JPEG Blob (${kbSize} KB)`;
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
     * Update Pipeline Stage Badge & Telemetry
     */
    setPipelineStage(stageText, isReady) {
        const el = this.elements.statPipelineStage;
        if (el) {
            el.textContent = stageText;
            if (isReady) {
                el.classList.add('ready');
            } else {
                el.classList.remove('ready');
            }
        }
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
        this.setPipelineStage('ERROR', false);
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

