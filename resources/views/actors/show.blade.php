@extends('layouts.app')

@section('assets')
    @vite(['resources/css/actor-detail.css', 'resources/js/actor-detail.js'])
@endsection

@section('content')
<div class="detail-container">
    
    <!-- Page Header -->
    <header class="detail-header">
        <a href="/" class="logo-badge" title="Back to Home">FD</a>
    </header>

    <!-- Navigation -->
    <section class="nav-section">
        <a href="/actors" id="btnBack" class="btn-back">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back
        </a>
    </section>

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
                    <span class="meta-label">Umur</span>
                    <span class="meta-value">{{ $actor->age ?? '-' }} Tahun</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Tanggal Lahir</span>
                    <span class="meta-value">{{ $actor->birth_date ? \Carbon\Carbon::parse($actor->birth_date)->translatedFormat('d F Y') : '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Tempat Lahir</span>
                    <span class="meta-value">{{ $actor->birth_place ?? $actor->nationality ?? '-' }}</span>
                </div>
            </div>

            <div class="biography-section">
                <div class="section-title">Biografi</div>
                <div class="biography-content">
                    {!! nl2br(e($actor->summary ?? 'Biografi belum tersedia untuk aktor ini.')) !!}
                </div>
            </div>

            <div class="filmography-section">
                <div class="section-title">Filmografi</div>
                @if($movies->isNotEmpty())
                    <ul class="filmography-list" id="filmographyList">
                        @foreach($movies as $movie)
                            <li class="filmography-item">
                                <span>{{ $movie->title }}</span>
                                <span class="film-year">{{ $movie->release_year }}</span>
                            </li>
                        @endforeach
                    </ul>
                @else
                    <p style="color: var(--text-muted); font-size: 14px; margin-top: 8px;">Belum ada data filmografi.</p>
                @endif
            </div>

        </div>
    </section>

</div>
@endsection
