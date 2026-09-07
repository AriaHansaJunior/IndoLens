/**
 * IndoLens - Phone Camera Capture Module (Session 1)
 * Manages device camera stream, live viewfinder, and in-memory frame capture.
 */

document.addEventListener('DOMContentLoaded', () => {
    CameraCapture.init();
});

const CameraCapture = {
    // Media Stream State
    mediaStream: null,
    currentFacingMode: 'environment', // 'environment' (rear camera) by default for phone-to-screen pointing
    isStreaming: false,
    isContinuousCaptureActive: false,
    continuousIntervalId: null,

    // Statistics & Counters
    totalFramesCaptured: 0,
    continuousFrameCount: 0,
    continuousStartTime: null,
    lastCapturedBlob: null,

    // DOM Elements Cache
    elements: {},

    /**
     * Entry Point
     */
    init() {
        this.cacheDOM();
        this.bindEvents();
        this.checkDeviceSupport();
    },

    /**
     * Cache DOM Elements
     */
    cacheDOM() {
        this.elements = {
            // Viewfinder & Video
            video: document.getElementById('cameraVideo'),
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
            btnLiveStream: document.getElementById('btnLiveStreamCapture'),
            btnStreamText: document.getElementById('btnStreamText'),
            btnStartPrompt: document.getElementById('btnStartPrompt'),

            // Telemetry Fields
            statStreamStatus: document.getElementById('statStreamStatus'),
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
     * Bind UI Event Listeners
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
            this.elements.btnCapture.addEventListener('click', () => this.captureSingleFrame());
        }

        if (this.elements.btnLiveStream) {
            this.elements.btnLiveStream.addEventListener('click', () => this.toggleContinuousCapture());
        }

        // Handle page visibility change (clean up stream when user navigates away)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isStreaming) {
                // Keep stream active or pause if needed
            }
        });
    },

    /**
     * Check browser mediaDevices support
     */
    checkDeviceSupport() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError('Camera access is not supported by this browser. Please use a modern browser (Chrome, Safari, Firefox, Edge) with HTTPS or localhost.');
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
     * Start Camera Stream
     */
    async startCamera() {
        this.hideError();
        this.updateStatus('connecting', 'Connecting...');

        // Flexible constraints: prefer environment camera, ideal 720p/1080p, no fixed resolution hard-lock
        const constraints = {
            audio: false,
            video: {
                facingMode: { ideal: this.currentFacingMode },
                width: { ideal: 1280 },
                height: { ideal: 720 },
            }
        };

        try {
            // First attempt with facingMode preference
            try {
                this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (err) {
                // Fallback to generic video if ideal facingMode failed (e.g. desktop webcam without environment mode)
                console.warn('Facing mode constraint failed, falling back to default video input:', err);
                this.mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            }

            const video = this.elements.video;
            video.srcObject = this.mediaStream;

            // Wait for video metadata to load dimensions
            await new Promise((resolve) => {
                video.onloadedmetadata = () => {
                    video.play();
                    resolve();
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

        // UI State Transitions
        if (this.elements.placeholder) this.elements.placeholder.style.display = 'none';
        if (video) video.style.display = 'block';
        if (this.elements.overlay) this.elements.overlay.style.display = 'block';
        if (this.elements.overlayPill) this.elements.overlayPill.style.display = 'flex';

        // Enable buttons
        if (this.elements.btnSwitch) this.elements.btnSwitch.disabled = false;
        if (this.elements.btnCapture) this.elements.btnCapture.disabled = false;
        if (this.elements.btnLiveStream) this.elements.btnLiveStream.disabled = false;

        // Update toggle button appearance
        if (this.elements.btnToggle) {
            this.elements.btnToggle.classList.remove('btn-start');
            this.elements.btnToggle.classList.add('btn-stop');
            if (this.elements.btnToggleText) this.elements.btnToggleText.textContent = 'Stop Camera';
        }

        // Read active camera label
        const track = this.mediaStream.getVideoTracks()[0];
        const trackSettings = track ? track.getSettings() : {};
        const deviceLabel = track ? (track.label || 'Connected Camera') : 'Default Camera';
        const activeFacing = trackSettings.facingMode || this.currentFacingMode;

        // Update telemetry
        this.updateStatus('active', 'Camera Active');
        if (this.elements.statStreamStatus) this.elements.statStreamStatus.textContent = 'Active (Live)';
        if (this.elements.statCameraDevice) this.elements.statCameraDevice.textContent = deviceLabel;
        if (this.elements.statResolution) this.elements.statResolution.textContent = `${width} × ${height} px`;
        if (this.elements.overlayResolution) this.elements.overlayResolution.textContent = `${width} × ${height}`;
        if (this.elements.overlayFacingMode) {
            this.elements.overlayFacingMode.textContent = activeFacing === 'user' ? 'Front (User)' : 'Rear (Environment)';
        }
    },

    /**
     * Stop Camera Stream
     */
    stopCamera() {
        if (this.isContinuousCaptureActive) {
            this.stopContinuousCapture();
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        const video = this.elements.video;
        if (video) {
            video.pause();
            video.srcObject = null;
            video.style.display = 'none';
        }

        this.isStreaming = false;

        // UI Reset
        if (this.elements.placeholder) this.elements.placeholder.style.display = 'flex';
        if (this.elements.overlay) this.elements.overlay.style.display = 'none';
        if (this.elements.overlayPill) this.elements.overlayPill.style.display = 'none';

        if (this.elements.btnSwitch) this.elements.btnSwitch.disabled = true;
        if (this.elements.btnCapture) this.elements.btnCapture.disabled = true;
        if (this.elements.btnLiveStream) this.elements.btnLiveStream.disabled = true;

        if (this.elements.btnToggle) {
            this.elements.btnToggle.classList.remove('btn-stop');
            this.elements.btnToggle.classList.add('btn-start');
            if (this.elements.btnToggleText) this.elements.btnToggleText.textContent = 'Start Camera';
        }

        this.updateStatus('idle', 'Camera Standby');
        if (this.elements.statStreamStatus) this.elements.statStreamStatus.textContent = 'Standby';
        if (this.elements.statCaptureRate) this.elements.statCaptureRate.textContent = '0 FPS';
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
     * Capture Single Frame into Memory
     * Proves that IndoLens can obtain and hold live camera frames.
     */
    captureSingleFrame() {
        if (!this.isStreaming) return;

        const video = this.elements.video;
        const canvas = this.elements.canvas;
        if (!video || !canvas) return;

        const width = video.videoWidth;
        const height = video.videoHeight;
        if (!width || !height) return;

        // Set canvas to frame resolution
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, width, height);

        // 1. Obtain raw pixel buffer (ImageData) - ready for future preprocessing
        const rawImageData = ctx.getImageData(0, 0, width, height);

        // 2. Export frame as JPEG Blob for network / storage transmission
        canvas.toBlob((blob) => {
            if (!blob) return;
            this.lastCapturedBlob = blob;
            this.totalFramesCaptured++;

            const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
            this.displayCapturedFrame({
                dataUrl: dataUrl,
                width: width,
                height: height,
                sizeBytes: blob.size,
                timestamp: new Date()
            });

            if (this.elements.statFramesCaptured) {
                this.elements.statFramesCaptured.textContent = String(this.totalFramesCaptured);
            }
        }, 'image/jpeg', 0.9);
    },

    /**
     * Display Captured Frame Preview and Metadata
     */
    displayCapturedFrame({ dataUrl, width, height, sizeBytes, timestamp }) {
        if (this.elements.capturedPlaceholder) {
            this.elements.capturedPlaceholder.style.display = 'none';
        }

        if (this.elements.capturedImagePreview) {
            this.elements.capturedImagePreview.src = dataUrl;
            this.elements.capturedImagePreview.style.display = 'block';
        }

        if (this.elements.capturedFrameTag) {
            this.elements.capturedFrameTag.textContent = `#${this.totalFramesCaptured} Available`;
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
        if (this.elements.statFrameBuffer) {
            this.elements.statFrameBuffer.textContent = `${width}×${height} (${kbSize} KB)`;
        }
    },

    /**
     * Toggle Continuous Live Frame Ingestion (Simulation of continuous live feed)
     */
    toggleContinuousCapture() {
        if (this.isContinuousCaptureActive) {
            this.stopContinuousCapture();
        } else {
            this.startContinuousCapture();
        }
    },

    startContinuousCapture() {
        if (!this.isStreaming) return;

        this.isContinuousCaptureActive = true;
        this.continuousFrameCount = 0;
        this.continuousStartTime = performance.now();

        if (this.elements.btnLiveStream) {
            this.elements.btnLiveStream.classList.add('active');
            if (this.elements.btnStreamText) this.elements.btnStreamText.textContent = 'Stop Stream Capture';
        }

        this.updateStatus('streaming', 'Stream Ingestion Active');

        // Sample frames at ~10 FPS (100ms interval) to demonstrate active continuous capture in memory
        this.continuousIntervalId = setInterval(() => {
            if (!this.isStreaming) {
                this.stopContinuousCapture();
                return;
            }

            this.captureSingleFrame();
            this.continuousFrameCount++;

            // Calculate live capture rate (FPS)
            const elapsedSeconds = (performance.now() - this.continuousStartTime) / 1000;
            if (elapsedSeconds > 0.5) {
                const currentFps = (this.continuousFrameCount / elapsedSeconds).toFixed(1);
                if (this.elements.statCaptureRate) {
                    this.elements.statCaptureRate.textContent = `${currentFps} FPS`;
                }
            }
        }, 100);
    },

    stopContinuousCapture() {
        if (this.continuousIntervalId) {
            clearInterval(this.continuousIntervalId);
            this.continuousIntervalId = null;
        }

        this.isContinuousCaptureActive = false;

        if (this.elements.btnLiveStream) {
            this.elements.btnLiveStream.classList.remove('active');
            if (this.elements.btnStreamText) this.elements.btnStreamText.textContent = 'Start Stream Capture';
        }

        if (this.isStreaming) {
            this.updateStatus('active', 'Camera Active');
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
