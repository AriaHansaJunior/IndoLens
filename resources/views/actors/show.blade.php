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
            Back
        </a>
    </header>

    <!-- Content Section -->
    <section class="detail-content">
        <!-- Photo -->
        <div class="actor-photo-wrapper">
            <img src="{{ asset('storage/' . $actor->photo) }}" alt="{{ $actor->full_name }}" class="actor-photo" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=400'">
        </div>

        <!-- Details -->
        <div class="actor-info">
            
            <div class="actor-name-group" data-actor-name="{{ $actor->full_name }}">
                <h1 class="actor-title">{{ $actor->full_name }}</h1>
                
                @if($actor->is_detected && $actor->current_character_name)
                    <div class="actor-character" id="actorCharacterLabel">Role: {{ $actor->current_character_name }}</div>
                    <div class="actor-hint" id="actorHintLabel" style="display:none;">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                        Play a film starring {{ $actor->full_name }} to detect character name
                    </div>
                @else
                    <div class="actor-character" id="actorCharacterLabel" style="display:none;"></div>
                    <div class="actor-hint" id="actorHintLabel">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                        Play a film starring {{ $actor->full_name }} to detect character name
                    </div>
                @endif
            </div>

            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Gender</span>
                    <span class="meta-value">{{ $actor->gender_label }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Age</span>
                    <span class="meta-value">{{ $actor->age ? $actor->age . ' Years Old' : '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Birth Date</span>
                    <span class="meta-value">{{ $actor->birth_date ? \Carbon\Carbon::parse($actor->birth_date)->format('F d, Y') : '-' }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Birth Place</span>
                    <span class="meta-value">{{ $actor->birth_place ?? '-' }}</span>
                </div>
            </div>

            <!-- Filmography & Character Roles from MySQL Database -->
            @if($actor->characters && $actor->characters->count() > 0)
                <div class="filmography-section">
                    <div class="section-title">Filmography &amp; Roles</div>
                    <ul class="filmography-list">
                        @foreach($actor->characters as $char)
                            <li class="filmography-item">
                                <span>
                                    <strong>{{ $char->movie->title ?? 'Unknown Film' }}</strong>
                                    &mdash;
                                    <em>Role: {{ $char->character_name }}</em>
                                </span>
                                @if($char->movie && $char->movie->release_year)
                                    <span class="film-year">{{ $char->movie->release_year }}</span>
                                @endif
                            </li>
                        @endforeach
                    </ul>
                </div>
            @endif

            <div class="biography-section">
                <div class="section-title">Biography</div>
                <div class="biography-content">
                    {!! nl2br(e($actor->biography ?? 'Biography is not yet available for this actor.')) !!}
                </div>
            </div>

            @if($actor->instagram || $actor->wikipedia || $actor->imdb)
                <div class="biography-section">
                    <div class="section-title">External Links</div>
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
