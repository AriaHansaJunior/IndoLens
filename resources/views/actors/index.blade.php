@extends('layouts.app')

@section('assets')
    @vite(['resources/css/actors.css', 'resources/js/actors.js'])
@endsection

@section('content')
<div class="actors-container">
    
    <!-- Page Header & Inline Search Bar -->
    <header class="actors-header-bar">
        <div class="header-title-wrap">
            <h1 class="page-title">Actor List</h1>
            <span class="actor-count-pill">{{ count($actors) }} {{ count($actors) === 1 ? 'Actor' : 'Actors' }}</span>
        </div>

        <!-- Compact Search Section -->
        <div class="search-section">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input type="text" id="actorSearchInput" class="search-input" placeholder="Search actor by name..." autocomplete="off">
        </div>
    </header>

    <!-- Compact Actors Grid -->
    <section class="actors-grid" id="actorsGrid">
        @forelse($actors as $actor)
            <div class="actor-card" data-name="{{ $actor->full_name }}" data-uuid="{{ $actor->uuid }}" data-is-known="{{ $actor->is_detected ? '1' : '0' }}">
                
                <div class="card-image-wrapper">
                    <img src="{{ $actor->photo_url }}" alt="{{ $actor->full_name }}" class="actor-photo" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=400'">
                    <span class="status-badge status-{{ $actor->is_detected ? 'known' : 'unknown' }}">
                        {{ $actor->is_detected ? 'KNOWN' : 'UNKNOWN' }}
                    </span>
                </div>
                
                <div class="card-content">
                    <div class="card-text-group">
                        <h2 class="actor-name" title="{{ $actor->full_name }}">{{ $actor->full_name }}</h2>
                        
                        @if($actor->is_detected && $actor->current_character_name)
                            <span class="actor-role-label">Role: {{ $actor->current_character_name }}</span>
                        @else
                            <span class="actor-role-label" style="display:none;">Role: -</span>
                        @endif
                    </div>
                    
                    <a href="{{ route('actors.show', $actor) }}" class="btn-detail">
                        <span>View Detail</span>
                    </a>
                </div>
            </div>
        @empty
            <div class="empty-state" id="emptyStateMessageDefault">
                <h3>No Actor Records Available</h3>
                <p>Actor records are not yet available in the database.</p>
            </div>
        @endforelse
        
        <!-- Hidden Empty State for JS Filtering -->
        <div class="empty-state" id="emptyStateMessage" style="display: none;">
            <h3>Actor Not Found</h3>
            <p>Try searching with a different keyword in the search bar.</p>
        </div>
    </section>

</div>
@endsection
