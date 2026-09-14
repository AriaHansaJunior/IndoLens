@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camp.css', 'resources/js/camp.js'])
@endsection

@section('content')
<div class="camp-form-container">

    <!-- Header Navigation -->
    <header class="camp-form-header">
        <a href="{{ route('camp.index') }}" class="btn-back">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            <span>Back to Camp</span>
        </a>
        <div class="form-title-group">
            <h1 class="page-title">Edit Actor</h1>
            <p class="camp-subtitle">Update information for {{ $actor->full_name }}</p>
        </div>
    </header>

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
                <strong>Please correct the following errors:</strong>
                <ul>
                    @foreach ($errors->all() as $error)
                        <li>{{ $error }}</li>
                    @endforeach
                </ul>
            </div>
        </div>
    @endif

    <!-- Edit Actor Form -->
    <form id="editActorForm" method="POST" action="{{ route('camp.update', $actor->id) }}" enctype="multipart/form-data" class="camp-form-card">
        @csrf
        @method('PUT')

        <div class="form-grid">
            <!-- Full Name (Required) -->
            <div class="form-group full-width">
                <label for="full_name" class="form-label">
                    Full Name <span class="required-star">*</span>
                </label>
                <input 
                    type="text" 
                    id="full_name" 
                    name="full_name" 
                    class="form-input @error('full_name') input-error @enderror" 
                    value="{{ old('full_name', $actor->full_name) }}" 
                    required 
                    autocomplete="off"
                >
                @error('full_name')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Gender -->
            <div class="form-group">
                <label class="form-label">Gender</label>
                @php
                    $selectedGender = old('gender', ($actor->gender_label && $actor->gender_label !== '-') ? $actor->gender_label : 'Male');
                @endphp
                <div class="radio-group">
                    <label class="radio-card">
                        <input 
                            type="radio" 
                            name="gender" 
                            value="Male" 
                            class="radio-input"
                            {{ in_array($selectedGender, ['Male', 'Laki-laki']) ? 'checked' : '' }}
                        >
                        <span class="radio-label-text">Male</span>
                    </label>
                    <label class="radio-card">
                        <input 
                            type="radio" 
                            name="gender" 
                            value="Female" 
                            class="radio-input"
                            {{ in_array($selectedGender, ['Female', 'Perempuan']) ? 'checked' : '' }}
                        >
                        <span class="radio-label-text">Female</span>
                    </label>
                </div>
                @error('gender')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Birth Date -->
            <div class="form-group">
                <label for="birth_date" class="form-label">Birth Date</label>
                <input 
                    type="date" 
                    id="birth_date" 
                    name="birth_date" 
                    class="form-input @error('birth_date') input-error @enderror" 
                    max="{{ date('Y-m-d') }}" 
                    value="{{ old('birth_date', $actor->birth_date) }}"
                >
                @error('birth_date')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Birth Place -->
            <div class="form-group">
                <label for="birth_place" class="form-label">Birth Place</label>
                <input 
                    type="text" 
                    id="birth_place" 
                    name="birth_place" 
                    class="form-input @error('birth_place') input-error @enderror" 
                    value="{{ old('birth_place', $actor->birth_place) }}"
                >
                @error('birth_place')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Age -->
            <div class="form-group">
                <label for="age" class="form-label">
                    Age
                    <span class="label-hint">(auto-calculates from Birth Date)</span>
                </label>
                <input 
                    type="number" 
                    id="age" 
                    name="age" 
                    class="form-input @error('age') input-error @enderror" 
                    min="0" 
                    max="150" 
                    value="{{ old('age', $actor->age) }}"
                >
                @error('age')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Primary Profile Photo -->
            <div class="form-group full-width">
                <label for="photo" class="form-label">
                    Primary Profile Photo
                    <span class="label-hint">(leave empty to keep current photo)</span>
                </label>
                
                @if($actor->photo)
                    <div class="current-photo-preview">
                        <span class="preview-label">Current Photo:</span>
                        <img src="{{ asset('storage/actors/' . $actor->photo) }}" alt="{{ $actor->full_name }}" class="photo-preview-thumb" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=100'">
                        <span class="current-photo-filename">{{ $actor->photo }}</span>
                    </div>
                @endif

                <input 
                    type="file" 
                    id="photo" 
                    name="photo" 
                    class="form-file-input @error('photo') input-error @enderror" 
                    accept=".jpg,.jpeg,.png"
                >
                <div id="photoPreviewContainer" class="photo-preview-wrap" style="display: none;">
                    <img id="photoPreviewImg" src="" alt="New Profile Photo Preview" class="photo-preview-thumb">
                    <span class="photo-preview-name" id="photoPreviewName"></span>
                </div>
                @error('photo')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Biography -->
            <div class="form-group full-width">
                <label for="biography" class="form-label">Biography</label>
                <textarea 
                    id="biography" 
                    name="biography" 
                    class="form-textarea @error('biography') input-error @enderror" 
                    rows="4"
                >{{ old('biography', $actor->biography) }}</textarea>
                @error('biography')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Instagram -->
            <div class="form-group">
                <label for="instagram" class="form-label">Instagram URL</label>
                <input 
                    type="url" 
                    id="instagram" 
                    name="instagram" 
                    class="form-input @error('instagram') input-error @enderror" 
                    value="{{ old('instagram', $actor->instagram) }}"
                >
                @error('instagram')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- Wikipedia -->
            <div class="form-group">
                <label for="wikipedia" class="form-label">Wikipedia URL</label>
                <input 
                    type="url" 
                    id="wikipedia" 
                    name="wikipedia" 
                    class="form-input @error('wikipedia') input-error @enderror" 
                    value="{{ old('wikipedia', $actor->wikipedia) }}"
                >
                @error('wikipedia')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>

            <!-- IMDb -->
            <div class="form-group full-width">
                <label for="imdb" class="form-label">IMDb URL</label>
                <input 
                    type="url" 
                    id="imdb" 
                    name="imdb" 
                    class="form-input @error('imdb') input-error @enderror" 
                    value="{{ old('imdb', $actor->imdb) }}"
                >
                @error('imdb')
                    <span class="field-error-msg">{{ $message }}</span>
                @enderror
            </div>
        </div>

        <div class="form-actions">
            <a href="{{ route('camp.index') }}" class="btn-secondary">Cancel</a>
            <button type="button" class="btn-primary" id="btnTriggerEditConfirm">
                Save Changes
            </button>
        </div>
    </form>

</div>

<!-- Edit Confirmation Modal -->
<div class="camp-modal-backdrop" id="editConfirmModal" style="display: none;">
    <div class="camp-modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
            <div class="modal-icon info-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12.01" y2="8"/>
                </svg>
            </div>
            <h3 class="modal-title">Confirm Changes</h3>
        </div>

        <div class="modal-body">
            <p class="modal-prompt">Are you sure you want to save these changes?</p>
        </div>

        <div class="modal-actions">
            <button type="button" class="btn-modal btn-cancel" id="btnCancelEdit">Cancel</button>
            <button type="button" class="btn-modal btn-primary" id="btnProceedEdit">Confirm</button>
        </div>
    </div>
</div>
@endsection
