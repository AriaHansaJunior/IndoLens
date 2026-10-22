@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camp.css', 'resources/js/camp.js'])
@endsection

@section('content')
<div class="camp-container">

    <!-- Page Header -->
    <header class="camp-header">
        <div class="camp-title-wrap">
            <h1 class="page-title">CAMP</h1>
            <p class="camp-subtitle">Actor Database Administration & Management</p>
        </div>
        <div class="camp-header-actions">
            <a href="{{ route('camp.create') }}" class="btn-primary btn-add-actor" id="btnAddActor">
                
                <span>Add New Actor</span>
            </a>
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

    <!-- Search Section -->
    <section class="camp-search-section">
        <form method="GET" action="{{ route('camp.index') }}" class="camp-search-form" id="campSearchForm">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input 
                type="text" 
                name="search" 
                id="campSearchInput" 
                class="search-input" 
                placeholder="Search actors..." 
                value="{{ request('search') }}" 
                autocomplete="off"
            >
            @if(request('search'))
                <a href="{{ route('camp.index', ['per_page' => $perPage]) }}" class="btn-clear-search" title="Clear Search">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </a>
            @endif
            <input type="hidden" name="per_page" value="{{ $perPage }}">
        </form>
    </section>

    <!-- Actors Table Card -->
    <section class="camp-table-card">
        <div class="table-responsive">
            <table class="camp-table">
                <thead>
                    <tr>
                        <th class="col-name">Actor Name</th>
                        <th class="col-actions">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse($actors as $actor)
                        <tr>
                            <td class="col-name">
                                <span class="actor-row-name">{{ $actor->full_name }}</span>
                            </td>
                            <td class="col-actions">
                                <div class="action-btn-group">
                                    <a href="{{ route('camp.edit', $actor->id) }}" class="btn-action btn-edit" title="Edit Actor Details">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                                        </svg>
                                        <span>Edit</span>
                                    </a>
                                    <a href="{{ route('camp.faces', $actor->id) }}" class="btn-action btn-face" title="Manage Face Reference Images">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                            <circle cx="8.5" cy="8.5" r="1.5"/>
                                            <polyline points="21 15 16 10 5 21"/>
                                        </svg>
                                        <span>Add Face</span>
                                    </a>
                                    <button 
                                        type="button" 
                                        class="btn-action btn-delete js-btn-delete" 
                                        data-actor-id="{{ $actor->id }}" 
                                        data-actor-name="{{ $actor->full_name }}"
                                        title="Delete Actor"
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
                            </td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="2" class="table-empty-state">
                                <p>No actors found matching your criteria.</p>
                            </td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>

        <!-- Table Footer: Rows Per Page & Pagination -->
        <div class="camp-table-footer">
            <div class="per-page-selector">
                <label for="perPageSelect">Rows per page:</label>
                <select id="perPageSelect" class="per-page-dropdown" onchange="window.location.href = this.value">
                    @foreach([5, 10, 25, 50] as $option)
                        <option value="{{ request()->fullUrlWithQuery(['per_page' => $option, 'page' => 1]) }}" {{ $perPage == $option ? 'selected' : '' }}>
                            {{ $option }}
                        </option>
                    @endforeach
                </select>
            </div>

            <div class="pagination-wrapper">
                {{ $actors->links('camp.pagination') }}
            </div>
        </div>
    </section>

</div>

<!-- Delete Actor Confirmation Modal -->
<div class="camp-modal-backdrop" id="deleteModalBackdrop" style="display: none;">
    <div class="camp-modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
            <div class="modal-icon warning-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
            </div>
            <h3 class="modal-title">Delete Actor</h3>
        </div>

        <div class="modal-body">
            <p class="modal-prompt">Are you sure you want to delete this actor?</p>
            <p class="modal-actor-target" id="deleteTargetActorName"></p>
            <p class="modal-warning">This action cannot be undone.</p>
        </div>

        <div class="modal-actions">
            <button type="button" class="btn-modal btn-cancel" id="btnCancelDelete">Cancel</button>
            <form id="deleteActorForm" method="POST" action="">
                @csrf
                @method('DELETE')
                <button type="submit" class="btn-modal btn-danger" id="btnConfirmDelete">Delete</button>
            </form>
        </div>
    </div>
</div>
@endsection
