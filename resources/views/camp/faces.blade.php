@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camp.css', 'resources/js/camp.js'])
@endsection

@section('content')
<div class="camp-faces-container">

    <!-- Header Navigation -->
    <header class="camp-form-header">
        <a href="{{ route('camp.index') }}" class="btn-back">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            <span>Back to Camp</span>
        </a>
        <div class="form-title-group">
            <h1 class="page-title">Manage Face Images</h1>
            <p class="camp-subtitle">Face recognition reference image dataset for <strong>{{ $actor->full_name }}</strong></p>
        </div>
    </header>

    <!-- Success Feedback Notification -->
    @if(session('success'))
        <div class="alert-success" id="campSuccessAlert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>{{ session('success') }}</span>
        </div>
    @endif

    <!-- Error Alert Banner -->
    @if ($errors->any())
        <div class="alert-danger">
            <div class="alert-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            </div>
            <div class="alert-content">
                <strong>Upload Error:</strong>
                <ul>
                    @foreach ($errors->all() as $error)
                        <li>{{ $error }}</li>
                    @endforeach
                </ul>
            </div>
        </div>
    @endif

    <!-- Multiple Face Image Upload Card -->
    <section class="camp-form-card upload-section">
        <h2 class="card-section-title">Upload Face Images</h2>
        <p class="section-desc">Select one or more face reference images for <strong>{{ $actor->full_name }}</strong>. Supported formats: <code>.jpg</code>, <code>.jpeg</code>, <code>.png</code>, <code>.webp</code>, <code>.avif</code>. No arbitrary quantity limit.</p>

        <form id="uploadFacesForm" method="POST" action="{{ route('camp.faces.store', $actor->id) }}" enctype="multipart/form-data">
            @csrf

            <div class="dropzone-area" id="facesDropzone">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="dropzone-icon">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p class="dropzone-text">Click to choose image files, or drag & drop here</p>
                <span class="dropzone-hint">Multiple selection enabled • JPG, JPEG, PNG, WEBP, AVIF</span>
                <input 
                    type="file" 
                    id="faceImagesInput" 
                    name="images[]" 
                    multiple 
                    accept=".jpg,.jpeg,.png,.webp,.avif"
                    class="dropzone-file-input"
                >
            </div>

            <!-- Client Preview Container for Selected Files -->
            <div id="selectedFilesContainer" class="selected-files-container" style="display: none;">
                <div class="preview-header">
                    <span class="preview-count" id="selectedCountText">0 images selected</span>
                    <button type="button" class="btn-clear-selection" id="btnClearSelection">Clear Selection</button>
                </div>
                <div class="selected-thumbnails-grid" id="selectedThumbnailsGrid"></div>
            </div>

            <div class="form-actions" style="margin-top: 24px;">
                <button type="button" class="btn-primary" id="btnTriggerUploadConfirm" disabled>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="17 8 12 3 7 8"/>
                        <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    <span>Upload Face Images</span>
                </button>
            </div>
        </form>
    </section>

    <!-- Existing Face Images Gallery Card -->
    <section class="camp-form-card gallery-section">
        <div class="gallery-header">
            <h2 class="card-section-title">Existing Face Images</h2>
            <span class="gallery-badge">{{ $actor->images->count() }} Images</span>
        </div>

        @if($actor->images->count() > 0)
            <div class="faces-gallery-grid">
                @foreach($actor->images as $img)
                    <div class="face-gallery-item" id="face-card-{{ $img->id }}">
                        <div class="face-img-wrapper">
                            <img src="{{ asset('storage/' . $img->image) }}" alt="{{ $actor->full_name }} Face Image" class="face-thumb" loading="lazy">
                        </div>
                        <div class="face-meta">
                            <span class="face-filename" title="{{ $img->image }}">{{ $img->image }}</span>
                            <button 
                                type="button" 
                                class="btn-delete-face js-btn-delete-face" 
                                data-actor-id="{{ $actor->id }}" 
                                data-image-id="{{ $img->id }}"
                                data-image-name="{{ $img->image }}"
                                title="Delete Face Image"
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="3 6 5 6 21 6"/>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                                    <line x1="10" y1="11" x2="10" y2="17"/>
                                    <line x1="14" y1="11" x2="14" y2="17"/>
                                </svg>
                                <span>Delete</span>
                            </button>
                        </div>
                    </div>
                @endforeach
            </div>
        @else
            <div class="faces-empty-state">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                </svg>
                <p>No face images uploaded for this actor yet.</p>
                <span>Upload one or more reference images above.</span>
            </div>
        @endif
    </section>

</div>

<!-- Upload Confirmation Modal -->
<div class="camp-modal-backdrop" id="uploadConfirmModal" style="display: none;">
    <div class="camp-modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
            <div class="modal-icon info-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
            </div>
            <h3 class="modal-title">Confirm Image Upload</h3>
        </div>

        <div class="modal-body">
            <p class="modal-prompt">Are you sure you want to upload these face images?</p>
            <p class="modal-actor-target" id="uploadCountSummary"></p>
        </div>

        <div class="modal-actions">
            <button type="button" class="btn-modal btn-cancel" id="btnCancelUpload">Cancel</button>
            <button type="button" class="btn-modal btn-primary" id="btnProceedUpload">Confirm</button>
        </div>
    </div>
</div>

<!-- Clear Selection Confirmation Modal -->
<div class="camp-modal-backdrop" id="clearSelectionModal" style="display: none;">
    <div class="camp-modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
            <div class="modal-icon warning-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            </div>
            <h3 class="modal-title">Clear Selection</h3>
        </div>

        <div class="modal-body">
            <p class="modal-prompt">Are you sure you want to delete this selection?</p>
            <p class="modal-warning">All currently selected images will be removed.</p>
        </div>

        <div class="modal-actions">
            <button type="button" class="btn-modal btn-cancel" id="btnCancelClearSelection">Cancel</button>
            <button type="button" class="btn-modal btn-danger" id="btnProceedClearSelection">Clear</button>
        </div>
    </div>
</div>

<!-- Delete Face Confirmation Modal -->
<div class="camp-modal-backdrop" id="deleteFaceModal" style="display: none;">
    <div class="camp-modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
            <div class="modal-icon warning-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            </div>
            <h3 class="modal-title">Delete Face Image</h3>
        </div>

        <div class="modal-body">
            <p class="modal-prompt">Are you sure you want to delete this face image?</p>
            <p class="modal-actor-target" id="deleteTargetFaceName"></p>
            <p class="modal-warning">This action cannot be undone.</p>
        </div>

        <div class="modal-actions">
            <button type="button" class="btn-modal btn-cancel" id="btnCancelDeleteFace">Cancel</button>
            <form id="deleteFaceForm" method="POST" action="">
                @csrf
                @method('DELETE')
                <button type="submit" class="btn-modal btn-danger" id="btnConfirmDeleteFace">Delete</button>
            </form>
        </div>
    </div>
</div>
@endsection
