@extends('layouts.app')

@section('assets')
    @vite(['resources/css/home.css', 'resources/js/home.js'])
@endsection

@section('content')

<!-- Video Player Section -->
<div class="video-section">
    <div class="video-wrapper" id="videoWrapper">
        <video id="mainVideo" class="video-element" playsinline muted loop></video>
        
        <!-- Video Fallback State if demo video is missing -->
        <div id="videoFallback" class="video-fallback-state" style="display: none;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            <div>
                <strong style="font-size: 16px; color: #FFFFFF;">Video demo belum tersedia</strong>
                <p style="font-size: 13px; margin-top: 4px;">Unggah klip film di bawah untuk memulai pengenalan wajah.</p>
            </div>
        </div>

        <!-- Overlay Layer -->
        <div id="videoOverlayLayer" class="video-overlay-layer"></div>

        <!-- Pause Mode Metadata Panel -->
        <div id="pauseMetadataPanel" class="pause-metadata-panel">
            <div id="metaActorName" class="actor-meta-title">Aktor Terdeteksi</div>
            <div id="metaCharacter" class="actor-meta-sub"></div>
            <div id="metaAge" class="actor-meta-detail"></div>
            <div id="metaFilmography" class="actor-meta-detail"></div>
        </div>
    </div>
</div>

<!-- Upload Area Section -->
<div class="upload-section">
    <div class="upload-card" id="uploadCard">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="upload-title">Upload Movie Clip</div>
        <div class="upload-subtitle">Drag & Drop atau <strong>Browse Video</strong></div>
        <div class="upload-formats">Format yang didukung: MP4, MOV, AVI, MKV</div>
        <input type="file" id="fileInput" class="hidden-file-input" accept=".mp4,.mov,.avi,.mkv">
    </div>
</div>

<!-- Progress Status Section -->
<div class="progress-container" id="progressContainer">
    <div class="progress-header">
        <div id="statusText" class="progress-status-text">
            <div class="spinner"></div> <span>Preparing...</span>
        </div>
    </div>
    <div class="progress-bar-bg">
        <div id="progressBarFill" class="progress-bar-fill"></div>
    </div>
</div>

<!-- Control Buttons Section -->
<div class="actions-section">
    <button type="button" id="btnBackDemo" class="btn btn-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        Back To Demo
    </button>

    <a href="/actors" id="btnActorList" class="btn btn-primary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
        </svg>
        Actor List
    </a>

    <a id="btnActorDetail" class="btn btn-secondary" disabled>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
        Actor Detail
    </a>
</div>

<!-- Modal Popup Confirmation -->
<div class="modal-backdrop" id="confirmModal">
    <div class="modal-card">
        <div class="modal-title">Kembali ke video demo?</div>
        <div class="modal-body">
            Video yang diunggah dan hasil pengenalan wajah akan ditutup.
        </div>
        <div class="modal-actions">
            <button type="button" id="modalCancelBtn" class="btn btn-secondary">Tidak</button>
            <button type="button" id="modalConfirmBtn" class="btn btn-primary">Ya</button>
        </div>
    </div>
</div>

@endsection
