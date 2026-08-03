@extends('layouts.app')

@section('assets')
    @vite(['resources/css/actors.css', 'resources/js/actors.js'])
@endsection

@section('content')
<div class="actors-container">
    
    <!-- Page Header -->
    <header class="actors-header">
        <a href="/" class="logo-badge" title="Back to Home">FD</a>
        <h1 class="page-title">Actor List</h1>
    </header>

    <!-- Search Section -->
    <section class="search-section">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="text" id="actorSearchInput" class="search-input" placeholder="Search Actor by name..." autocomplete="off">
    </section>

    <!-- Actors Grid -->
    <section class="actors-grid" id="actorsGrid">
        @forelse($actors as $actor)
            <div class="actor-card" data-name="{{ $actor->full_name }}" data-id="{{ $actor->id }}">
                
                <div class="card-image-wrapper">
                    <!-- Assuming photo contains filename like 'bayu_skak.jpg'. Adjust path based on your storage structure -->
                    <img src="{{ asset('storage/actors/' . $actor->photo) }}" alt="{{ $actor->full_name }}" class="actor-photo" onerror="this.src='https://ui-avatars.com/api/?name={{ urlencode($actor->full_name) }}&background=0D1321&color=165DFF&size=400'">
                </div>
                
                <div class="card-content">
                    <h2 class="actor-name">{{ $actor->full_name }}</h2>
                    
                    <span class="status-badge status-{{ strtolower($status ?? 'known') }}">
                        {{ $status ?? 'Known' }}
                    </span>
                    
                    <a href="/actors/{{ $actor->id }}" class="btn-detail">
                        View Detail
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M5 12h14M12 5l7 7-7 7"/>
                        </svg>
                    </a>
                </div>
            </div>
        @empty
            <div class="empty-state" id="emptyStateMessageDefault">
                <h3>Belum ada aktor yang dikenali</h3>
                <p>Silakan upload video demonstrasi pada halaman utama terlebih dahulu.</p>
            </div>
        @endforelse
        
        <!-- Hidden Empty State for JS Filtering -->
        <div class="empty-state" id="emptyStateMessage" style="display: none;">
            <h3>Aktor tidak ditemukan</h3>
            <p>Cobalah kata kunci lain di kolom pencarian.</p>
        </div>
    </section>

</div>
@endsection
