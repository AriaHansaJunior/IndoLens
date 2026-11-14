@extends('layouts.app')

@section('assets')
    @vite(['resources/css/actor-detail.css', 'resources/js/actor-detail.js'])
@endsection

@section('content')
<div class="detail-container">

    <section class="detail-content">
        
        <div class="actor-photo-wrapper">
            <img src="{{ $actor->photo_url }}" alt="{{ $actor->full_name }}" class="actor-photo" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=400'">
            
            <div class="photo-badge-overlay">
                <span class="status-badge status-{{ $actor->is_detected ? 'known' : 'unknown' }}" id="actorDetailStatusBadge">
                    {{ $actor->is_detected ? 'KNOWN' : 'UNKNOWN' }}
                </span>
            </div>
        </div>

        <!-- Right: Actor Information Panel -->
        <div class="actor-info">
            
            <!-- Actor Name & Detected Character -->
            <div class="actor-name-group" data-actor-name="{{ $actor->full_name }}">
                <div class="actor-title-row">
                    <h1 class="actor-title">{{ $actor->full_name }}</h1>
                    @if($actor->is_detected && $actor->current_character_name)
                        <span class="actor-character-pill" id="actorCharacterLabel">Role: {{ $actor->current_character_name }}</span>
                    @else
                        <span class="actor-character-pill" id="actorCharacterLabel" style="display:none;"></span>
                    @endif
                </div>
            </div>

            <!-- Compact Metadata Row -->
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

            <!-- Side-by-side Filmography & Biography Row -->
            <div class="detail-split-row">
                
                <!-- Filmography & Character Roles -->
                <div class="detail-sub-card filmography-card">
                    <div class="section-title">Filmography &amp; Roles</div>
                    @if($actor->characters && $actor->characters->count() > 0)
                        <ul class="filmography-list" id="filmographyList">
                            @foreach($actor->characters as $char)
                                <li class="filmography-item">
                                    <div class="film-info">
                                        <span class="film-title">{{ $char->movie->title ?? 'Unknown Film' }}</span>
                                        <span class="film-role">Role: {{ $char->character_name }}</span>
                                    </div>
                                    @if($char->movie && $char->movie->release_year)
                                        <span class="film-year">{{ $char->movie->release_year }}</span>
                                    @endif
                                </li>
                            @endforeach
                        </ul>
                    @else
                        <p class="empty-sub-text">No recorded movie roles.</p>
                    @endif
                </div>

                <!-- Biography -->
                <div class="detail-sub-card biography-card">
                    <div class="section-title">Biography</div>
                    <div class="biography-content">
                        {!! nl2br(e($actor->biography ?? 'Biography is not yet available for this actor.')) !!}
                    </div>
                </div>

            </div>

            <!-- External Links (if available) -->
            @if($actor->instagram || $actor->wikipedia || $actor->imdb)
                <div class="links-row">
                    <span class="links-label">External Profiles:</span>
                    <div class="links-group">
                        @if($actor->instagram)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->instagram, ['http://', 'https://']) ? $actor->instagram : 'https://' . $actor->instagram }}" target="_blank" rel="noopener noreferrer" class="link-pill">
                                <span>Instagram</span>
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
                            </a>
                        @endif
                        @if($actor->wikipedia)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->wikipedia, ['http://', 'https://']) ? $actor->wikipedia : 'https://' . $actor->wikipedia }}" target="_blank" rel="noopener noreferrer" class="link-pill">
                                <span>Wikipedia</span>
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
                            </a>
                        @endif
                        @if($actor->imdb)
                            <a href="{{ \Illuminate\Support\Str::startsWith($actor->imdb, ['http://', 'https://']) ? $actor->imdb : 'https://' . $actor->imdb }}" target="_blank" rel="noopener noreferrer" class="link-pill">
                                <span>IMDb</span>
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
                            </a>
                        @endif
                    </div>
                </div>
            @endif

        </div>
    </section>

</div>
@endsection
