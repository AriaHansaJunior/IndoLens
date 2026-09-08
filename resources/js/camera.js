/**
 * IndoLens - Real-Time YOLO Face Detection Module (Session 3)
 * Integrates real-time camera frames with Ultralytics YOLOv8 face detection,
 * tracks face bounding boxes over the live video viewfinder, and exposes
 * bounding box coordinates without performing FaceNet or actor recognition.
 */

document.addEventListener('DOMContentLoaded', () => {
    CameraCapture.init();
});

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

    // Real-Time YOLO Face Detection State (Session 3)
    detectionCanvas: null,
    detectionCtx: null,
    isDetectionInFlight: false,
    latestDetections: [],
    facesDetectedCount: 0,
    lastYoloInferenceMs: 0,

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
            statYoloLatency: document.getElementById('statYoloLatency'),
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
        this.yoloCanvas = document.createElement('canvas');
        this.yoloCtx = this.yoloCanvas.getContext('2d');
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
            video.srcObject = this.mediaStream;

            // Wait for video metadata to establish dimensions
            await new Promise((resolve) => {
                video.onloadedmetadata = () => {
                    video.play().then(resolve).catch(resolve);
                };
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

        // Update telemetry for active pipeline
        this.updateStatus('streaming', 'Pipeline Active');
        this.setPipelineStage('YOLO ACTIVE', true);

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

        // 2. Update Latest Frame Buffer State (In-place O(1) update)
        this.totalFramesIngested++;
        this.latestFrame.frameNumber = this.totalFramesIngested;
        this.latestFrame.timestamp = Date.now();
        this.latestFrame.width = width;
        this.latestFrame.height = height;
        this.latestFrame.status = 'READY_FOR_YOLO';

        // 3. Update Real-Time Telemetry
        if (this.elements.statFramesCaptured) {
            this.elements.statFramesCaptured.textContent = String(this.totalFramesIngested);
        }

        if (this.elements.statFrameBuffer) {
            this.elements.statFrameBuffer.textContent = `${width} × ${height} px • Frame #${this.totalFramesIngested} (Ready)`;
        }

        // Calculate live acquisition rate (FPS)
        const elapsedSeconds = (performance.now() - this.pipelineStartTime) / 1000;
        if (elapsedSeconds > 0.5) {
            const currentFps = (this.totalFramesIngested / elapsedSeconds).toFixed(1);
            if (this.elements.statCaptureRate) {
                this.elements.statCaptureRate.textContent = `${currentFps} FPS`;
            }
        }

        // 4. DISPATCH FRAME TO YOLO FACE DETECTION (Session 3)
        if (!this.isDetectionInFlight) {
            this.triggerYoloDetection();
        }
    },

    /**
     * Send Latest Frame to YOLO Face Detection Endpoint
     * Endpoint: POST /api/yolo/detect (proxied to Python micro-service)
     * Retrieves latest frame from window.IndoLensPipeline.getLatestFrame()
     */
    async triggerYoloDetection() {
        if (!this.isStreaming || !this.isPipelineActive || this.isDetectionInFlight) return;

        const frame = (window.IndoLensPipeline && typeof window.IndoLensPipeline.getLatestFrame === 'function')
            ? window.IndoLensPipeline.getLatestFrame()
            : this.getLatestFrame();

        if (!frame || !frame.canvas || !frame.width || !frame.height) return;

        this.isDetectionInFlight = true;
        const startTime = performance.now();

        try {
            // Use the downsampled YOLO canvas blob
            // Lower quality to 0.70 for ultra-fast mobile encoding (virtually no impact on YOLOv8)
            const blob = await new Promise((resolve) =>
                this.yoloCanvas.toBlob(resolve, 'image/jpeg', 0.70)
            );
            if (!blob || !this.isStreaming || !this.isPipelineActive) {
                this.isDetectionInFlight = false;
                return;
            }

            const response = await fetch('/api/yolo/detect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'image/jpeg',
                },
                body: blob
            });

            if (!response.ok) {
                throw new Error(`YOLO detection failed (HTTP ${response.status})`);
            }

            const data = await response.json();
            const totalLatencyMs = Math.round(performance.now() - startTime);

            if (data.status === 'success' && this.isStreaming && this.isPipelineActive) {
                this.latestDetections = data.faces || [];
                this.facesDetectedCount = data.faces_count || 0;
                this.lastYoloInferenceMs = data.inference_time_ms || totalLatencyMs;

                // Update telemetry fields
                this.updateYoloTelemetry(this.facesDetectedCount, this.lastYoloInferenceMs);

                // Render bounding boxes over live viewfinder
                this.renderBoundingBoxes(this.latestDetections, data.frame_dimensions);
            }
        } catch (err) {
            console.warn('[YOLO Detection Notice]', err.message);
        } finally {
            this.isDetectionInFlight = false;
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

            // 1. Semi-transparent subtle tint inside bounding box
            ctx.fillStyle = 'rgba(0, 229, 255, 0.08)';
            ctx.fillRect(boxX, boxY, boxW, boxH);

            // 2. Primary bounding box border
            ctx.strokeStyle = '#00E5FF';
            ctx.lineWidth = 2;
            ctx.strokeRect(boxX, boxY, boxW, boxH);

            // 3. High-tech corner brackets (AI reticle accent)
            const cornerLen = Math.min(16, Math.floor(Math.min(boxW, boxH) * 0.25));
            ctx.strokeStyle = '#00FF66';
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

            // 4. Confidence Badge Pill above bounding box
            const confPercent = Math.round(confidence * 100);
            const labelText = `Face ${confPercent}%`;

            ctx.font = '600 11px "Inter", -apple-system, BlinkMacSystemFont, sans-serif';
            const textMetrics = ctx.measureText(labelText);
            const badgeW = textMetrics.width + 14;
            const badgeH = 20;
            const badgeX = boxX;
            const badgeY = Math.max(4, boxY - badgeH - 4);

            // Badge background pill
            ctx.fillStyle = 'rgba(5, 7, 14, 0.9)';
            ctx.beginPath();
            ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
            ctx.fill();

            // Badge border
            ctx.strokeStyle = 'rgba(0, 229, 255, 0.5)';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Tiny neon indicator dot
            ctx.fillStyle = '#00FF66';
            ctx.beginPath();
            ctx.arc(badgeX + 6, badgeY + badgeH / 2, 2.5, 0, Math.PI * 2);
            ctx.fill();

            // Text label
            ctx.fillStyle = '#FFFFFF';
            ctx.fillText(labelText, badgeX + 13, badgeY + badgeH - 5.5);
        });
    },

    /**
     * Update YOLO Telemetry in UI
     */
    updateYoloTelemetry(facesCount, inferenceMs) {
        const countEl = this.elements.statFacesCount;
        const latencyEl = this.elements.statYoloLatency;

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
        this.updateYoloTelemetry(0, 0);

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
        this.updateYoloTelemetry(0, 0);
        if (this.elements.statStreamStatus) this.elements.statStreamStatus.textContent = 'Standby';
        if (this.elements.statCameraDevice) this.elements.statCameraDevice.textContent = 'None';
        if (this.elements.statResolution) this.elements.statResolution.textContent = '-';
        if (this.elements.statCaptureRate) this.elements.statCaptureRate.textContent = '0 FPS';
        if (this.elements.statFrameBuffer) this.elements.statFrameBuffer.textContent = '-';
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

