@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camera.css', 'resources/js/camera.js'])
@endsection

@section('content')
<div class="camera-page-container">
    
    <!-- Clean Page Header -->
    <header class="camera-page-header">
        <div class="header-titles">
            <h1 class="page-title">Live Camera Recognition</h1>
            <p class="page-subtitle">Real-time actor identification stream powered by YOLOv8 &amp; FaceNet</p>
        </div>
        <div class="stream-status-pill" id="cameraStatusBadge">
            <span class="status-indicator-dot" id="cameraStatusDot"></span>
            <span id="cameraStatusText">Standby</span>
        </div>
    </header>

    <!-- Main Camera Layout (80% Camera, 20% Detected Faces) -->
    <div class="camera-grid">
        
        <!-- Left (80%): Live Viewfinder -->
        <div class="viewfinder-card">
            
            <div class="viewfinder-container" id="viewfinderContainer">
                
                <!-- Live Video Element -->
                <video id="cameraVideo" class="camera-video" playsinline autoplay muted style="display: none;"></video>
                
                <!-- Real-Time Face Detection Bounding Box Canvas -->
                <canvas id="detectionCanvas" class="detection-canvas" style="display: none;"></canvas>

                <!-- Hidden Canvas for Frame Grab -->
                <canvas id="captureCanvas" class="hidden-canvas" style="display: none;"></canvas>

                <!-- Reticle Overlay / Framing Guide -->
                <div class="viewfinder-overlay" id="viewfinderOverlay">
                    <div class="reticle-corner top-left"></div>
                    <div class="reticle-corner top-right"></div>
                    <div class="reticle-corner bottom-left"></div>
                    <div class="reticle-corner bottom-right"></div>
                    <div class="reticle-center-guide"></div>
                </div>

                <!-- Feed Telemetry Pill (Resolution & Facing) -->
                <div class="video-overlay-pill" id="videoOverlayPill" style="display: none;">
                    <span id="overlayResolution">0 × 0</span>
                    <span class="pill-separator">•</span>
                    <span id="overlayFacingMode">Environment</span>
                </div>

                <!-- Video State Indicator Pill (Running vs Paused) -->
                <div class="video-state-pill" id="videoStatePill" style="display: none;">
                    <span class="video-state-icon" id="videoStateIcon">▶</span>
                    <span id="videoStateText">Video Running</span>
                </div>

                <!-- Pause Action Overlay (Open Actor Detail) -->
                <div class="pause-action-overlay" id="pauseActionOverlay" style="display: none;"></div>

                <!-- Standby Placeholder -->
                <div class="viewfinder-placeholder" id="cameraPlaceholder">
                    <div class="placeholder-icon-wrap">
                        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                            <circle cx="12" cy="13" r="4"/>
                        </svg>
                    </div>
                    <h3 class="placeholder-title">Camera Feed Idle</h3>
                    <p class="placeholder-desc">Click <strong>Start Camera</strong> to begin real-time face detection and recognition.</p>
                    <button type="button" id="btnStartPrompt" class="btn-primary-start">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                        <span>Start Camera</span>
                    </button>
                </div>

                <!-- Error Notice Banner -->
                <div class="camera-error-banner" id="cameraErrorBanner" style="display: none;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <span id="cameraErrorMessage">Unable to access camera. Please check permissions.</span>
                </div>

            </div>

            <!-- Compact Camera Controls Bar -->
            <div class="camera-controls-bar">
                <div class="controls-left">
                    <button type="button" id="btnToggleCamera" class="btn-control btn-start">
                        <svg class="icon-play" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg>
                        <span id="btnToggleText">Start Camera</span>
                    </button>

                    <button type="button" id="btnSwitchCamera" class="btn-control btn-secondary" title="Flip Camera" disabled>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 16v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4"/>
                            <path d="M4 8V4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/>
                            <polyline points="16 12 20 8 24 12"/>
                            <polyline points="8 12 4 16 0 12"/>
                        </svg>
                        <span>Flip</span>
                    </button>
                </div>

                <!-- Discreet Snapshot Action -->
                <div class="controls-right">
                    <button type="button" id="btnCaptureFrame" class="btn-control btn-capture-subtle" title="Snapshot Frame" disabled>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <circle cx="12" cy="12" r="3"/>
                        </svg>
                        <span>Snapshot</span>
                    </button>
                </div>
            </div>

        </div>

        <!-- Right (20%): Detected Faces & Recognition Results Panel -->
        <div class="detected-panel">
            
            <div class="detected-panel-header">
                <div class="detected-title-wrap">
                    <h2 class="panel-title">Faces Detected</h2>
                    <span class="face-count-badge" id="statFacesCount">0</span>
                </div>
            </div>

            <!-- Dynamic Detected Faces List -->
            <div class="detected-faces-container">
                <div class="empty-faces-note" id="emptyFacesNote">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M8 15s1.5 2 4 2 4-2 4-2"/>
                        <line x1="9" y1="9" x2="9.01" y2="9"/>
                        <line x1="15" y1="9" x2="15.01" y2="9"/>
                    </svg>
                    <span>No faces detected in current frame</span>
                </div>
                
                <div class="detected-faces-list" id="detectedFacesList"></div>
            </div>

            <!-- Compact Telemetry Summary Footer -->
            <div class="telemetry-compact-footer">
                <div class="stat-mini">
                    <span class="mini-label">Inference</span>
                    <span class="mini-val" id="statYoloLatency">0 ms</span>
                </div>
                <div class="stat-mini">
                    <span class="mini-label">Embedding</span>
                    <span class="mini-val" id="statFaceNetLatency">0 ms</span>
                </div>
            </div>

        </div>

    </div>

</div>
@endsection
