@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camera.css', 'resources/js/camera.js'])
@endsection

@section('content')
<div class="camera-page-container">
    
    <!-- Page Header -->
    <header class="camera-page-header">
        <div class="header-titles">
            <div class="header-badge">
                <span class="pulse-dot"></span>
                <span>Camera Stream Ingestion</span>
            </div>
            <h1 class="page-title">Live Camera Capture</h1>
            <p class="page-subtitle">Direct camera frame acquisition for the IndoLens pipeline.</p>
        </div>

        <div class="stream-status-badge" id="cameraStatusBadge">
            <span class="status-indicator-dot" id="statusDot"></span>
            <span id="cameraStatusText">Camera Standby</span>
        </div>
    </header>

    <!-- Main Camera Grid / Layout -->
    <div class="camera-grid">
        
        <!-- Left / Top: Live Viewfinder View -->
        <div class="viewfinder-card">
            
            <div class="viewfinder-container" id="viewfinderContainer">
                
                <!-- Live Video Element (Hidden until stream starts) -->
                <video id="cameraVideo" class="camera-video" playsinline autoplay muted style="display: none;"></video>
                
                <!-- Real-Time Face Detection Bounding Box Canvas (Hidden until stream starts) -->
                <canvas id="detectionCanvas" class="detection-canvas" style="display: none;"></canvas>

                <!-- Hidden Canvas for Memory Frame Grab -->
                <canvas id="captureCanvas" class="hidden-canvas" style="display: none;"></canvas>

                <!-- Reticle Overlay / Framing Guide -->
                <div class="viewfinder-overlay" id="viewfinderOverlay">
                    <div class="reticle-corner top-left"></div>
                    <div class="reticle-corner top-right"></div>
                    <div class="reticle-corner bottom-left"></div>
                    <div class="reticle-corner bottom-right"></div>
                    <div class="reticle-center-guide"></div>
                </div>

                <!-- Feed Telemetry Pill (Overlaid on video) -->
                <div class="video-overlay-pill" id="videoOverlayPill" style="display: none;">
                    <span id="overlayResolution">0 × 0</span>
                    <span class="pill-separator">•</span>
                    <span id="overlayFacingMode">Environment</span>
                </div>

                <!-- Standby / Permission Prompt Placeholder -->
                <div class="viewfinder-placeholder" id="cameraPlaceholder">
                    <div class="placeholder-icon-wrap">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                            <circle cx="12" cy="13" r="4"/>
                        </svg>
                    </div>
                    <h3 class="placeholder-title">Camera Feed Idle</h3>
                    <p class="placeholder-desc">Grant camera permission and click <strong>Start Camera</strong> to begin capturing live video frames.</p>
                    <button type="button" id="btnStartPrompt" class="btn-primary">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                        Start Camera
                    </button>
                    <a href="/ca.crt" class="btn-cert-download" download="indolens-ca.crt" title="Download Local CA Certificate for Phone SSL">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        Download SSL CA Certificate
                    </a>
                </div>

                <!-- Error Notice Container -->
                <div class="camera-error-banner" id="cameraErrorBanner" style="display: none;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <span id="cameraErrorMessage">Unable to access camera. Please verify camera permissions.</span>
                </div>

            </div>

            <!-- Controls Toolbar -->
            <div class="camera-controls-bar">
                <div class="controls-group main-actions">
                    <button type="button" id="btnToggleCamera" class="btn-control btn-start">
                        <svg class="icon-play" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                        <span id="btnToggleText">Start Camera</span>
                    </button>

                    <button type="button" id="btnSwitchCamera" class="btn-control btn-secondary" title="Switch between Rear and Front Camera" disabled>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 16v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4"/>
                            <path d="M4 8V4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/>
                            <polyline points="16 12 20 8 24 12"/>
                            <polyline points="8 12 4 16 0 12"/>
                        </svg>
                        <span>Flip Camera</span>
                    </button>
                </div>

                <div class="controls-group capture-actions">
                    <button type="button" id="btnCaptureFrame" class="btn-control btn-capture" title="Capture Single Frame into Memory" disabled>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <circle cx="12" cy="12" r="3"/>
                        </svg>
                        <span>Capture Frame</span>
                    </button>

                    <button type="button" id="btnLiveStreamCapture" class="btn-control btn-stream" title="Continuous Live Frame Ingestion" disabled>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M2 12h4l3 9 6-18 3 9h4"/>
                        </svg>
                        <span id="btnStreamText">Start Stream Capture</span>
                    </button>
                </div>
            </div>

        </div>

        <!-- Right / Bottom: Stream Telemetry & Captured Frame Panel -->
        <div class="telemetry-card">
            
            <h2 class="card-title">Stream Telemetry</h2>

            <!-- Metrics Grid -->
            <div class="telemetry-grid">
                
                <div class="telemetry-item">
                    <span class="telemetry-label">Stream Status</span>
                    <span class="telemetry-value highlight" id="statStreamStatus">Inactive</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Pipeline Stage</span>
                    <span class="telemetry-value highlight-stage" id="statPipelineStage">STANDBY</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Faces Detected</span>
                    <span class="telemetry-value highlight-faces" id="statFacesCount">0</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">YOLO Inference</span>
                    <span class="telemetry-value" id="statYoloLatency">0 ms</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Active Device</span>
                    <span class="telemetry-value" id="statCameraDevice">None</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Native Resolution</span>
                    <span class="telemetry-value" id="statResolution">-</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Frames Ingested</span>
                    <span class="telemetry-value counter" id="statFramesCaptured">0</span>
                </div>

                <div class="telemetry-item">
                    <span class="telemetry-label">Pipeline Rate</span>
                    <span class="telemetry-value" id="statCaptureRate">0 FPS</span>
                </div>

                <div class="telemetry-item" style="grid-column: span 2;">
                    <span class="telemetry-label">Latest Frame Buffer</span>
                    <span class="telemetry-value" id="statFrameBuffer">-</span>
                </div>

            </div>

            <!-- Latest Captured Frame Preview -->
            <div class="captured-preview-section">
                <div class="section-sub-header">
                    <h3 class="section-sub-title">Latest Captured Frame</h3>
                    <span class="frame-tag" id="capturedFrameTag">No Frame Yet</span>
                </div>

                <div class="captured-frame-box" id="capturedFrameBox">
                    <img id="capturedImagePreview" src="" alt="Latest Frame Preview" style="display: none;" class="captured-img">
                    <div class="captured-empty-placeholder" id="capturedPlaceholder">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                            <circle cx="8.5" cy="8.5" r="1.5"/>
                            <polyline points="21 15 16 10 5 21"/>
                        </svg>
                        <span>Captured frame data will appear here</span>
                    </div>
                </div>

                <div class="captured-meta" id="capturedMeta" style="display: none;">
                    <div class="meta-row">
                        <span class="meta-key">Captured At:</span>
                        <span class="meta-val" id="metaTimestamp">-</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-key">Dimensions:</span>
                        <span class="meta-val" id="metaDimensions">-</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-key">Memory Format:</span>
                        <span class="meta-val highlight-green" id="metaFormat">JPEG Blob (Available)</span>
                    </div>
                </div>
            </div>

        </div>

    </div>

</div>
@endsection
