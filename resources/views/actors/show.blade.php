@extends('layouts.app')

@section('assets')
    @vite(['resources/css/actor-detail.css', 'resources/js/actor-detail.js'])
@endsection

@section('content')
<div class="detail-container">
    
    <!-- Page Header -->
    <header class="detail-header">
        <a href="/actors" id="btnBack" class="btn-back">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Kembali
        </a>
    </header>

    <!-- Content Section -->
    <section class="detail-content">
        <!-- Photo -->
        <div class="actor-photo-wrapper">
            <img src="{{ asset('storage/actors/' . $actor->photo) }}" alt="{{ $actor->full_name }}" class="actor-photo" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=400'">
        </div>

        <!-- Details -->
        <div class="actor-info">
            
            <div class="actor-name-group">
                <h1 class="actor-title">{{ $actor->full_name }}</h1>
                @if($character)
                    <div class="actor-character">Sebagai: {{ $character->character_name }}</div>
                @endif
            </div>

            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Jenis Kelamin</span>
                    <span class="meta-value">{{ $actor->gender ?? '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Umur</span>
                    <span class="meta-value">{{ $actor->age ? $actor->age . ' Tahun' : '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Tanggal Lahir</span>
                    <span class="meta-value">{{ $actor->birth_date ? \Carbon\Carbon::parse($actor->birth_date)->translatedFormat('d F Y') : '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Tempat Lahir</span>
                    <span class="meta-value">{{ $actor->birth_place ?? '-' }}</span>
                </div>
            </div>

            <div class="biography-section">
                <div class="section-title">Biografi</div>
                <div class="biography-content">
                    {!! nl2br(e($actor->biography ?? 'Biografi belum tersedia untuk aktor ini.')) !!}
                </div>
            </div>

            @if($actor->instagram || $actor->wikipedia || $actor->imdb)
                <div class="biography-section">
                    <div class="section-title">Tautan Luar</div>
                    <div class="biography-content" style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px;">
                        @if($actor->instagram)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->instagram, ['http://', 'https://']) ? $actor->instagram : 'https://' . $actor->instagram }}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">Instagram</a>
                        @endif
                        @if($actor->wikipedia)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->wikipedia, ['http://', 'https://']) ? $actor->wikipedia : 'https://' . $actor->wikipedia }}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">Wikipedia</a>
                        @endif
                        @if($actor->imdb)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->imdb, ['http://', 'https://']) ? $actor->imdb : 'https://' . $actor->imdb }}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">IMDb</a>
                        @endif
                    </div>
                </div>
            @endif

        </div>
    </section>

</div>
@endsection
