@extends('layouts.app')

@section('assets')
    @vite(['resources/css/camp.css', 'resources/js/camp.js'])
@endsection

@section('content')
<div class="camp-faces-container">

    <header class="camp-form-header">
        <div class="form-title-group">
            <h1 class="page-title">Manage Roles &amp; Filmography</h1>
            <p class="camp-subtitle">Database filmography &amp; live recognition keywords for <strong>{{ $actor->full_name }}</strong></p>
        </div>
    </header>

    @if(session('success'))
        <div class="alert-success" id="campSuccessAlert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>{{ session('success') }}</span>
        </div>
    @endif

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

    <div class="roles-vertical-stack">

        <!-- Section 1: Filmography Characters (movies + characters tables) -->
        <section class="camp-form-card">
            <h2 class="card-section-title">Filmography Characters</h2>
            <p class="section-desc">Shown on the public Actor Detail page. Select a movie or create a new one.</p>

            <form method="POST" action="{{ route('camp.characters.store', $actor) }}" style="margin-bottom: 24px;">
                @csrf

                <div class="form-grid">
                    <div class="form-group">
                        <label for="movie_id" class="form-label">Existing Movie <span class="label-hint">(optional if adding new movie below)</span></label>
                        <select id="movie_id" name="movie_id" class="form-select">
                            <option value="">-- Add New Movie Title Below --</option>
                            @foreach($movies as $movie)
                                <option value="{{ $movie->id }}" {{ old('movie_id') == $movie->id ? 'selected' : '' }}>
                                    {{ $movie->title }}{{ $movie->release_year ? ' (' . $movie->release_year . ')' : '' }}
                                </option>
                            @endforeach
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="new_movie_title" class="form-label">New Movie Title</label>
                        <input type="text" id="new_movie_title" name="new_movie_title" class="form-input" placeholder="e.g. Lara Ati" value="{{ old('new_movie_title') }}">
                    </div>

                    <div class="form-group">
                        <label for="new_movie_year" class="form-label">Release Year</label>
                        <input type="number" id="new_movie_year" name="new_movie_year" class="form-input" placeholder="e.g. 2022" min="1900" max="2100" value="{{ old('new_movie_year') }}">
                    </div>

                    <div class="form-group">
                        <label for="new_movie_genre" class="form-label">Genre</label>
                        <input type="text" id="new_movie_genre" name="new_movie_genre" class="form-input" placeholder="e.g. Comedy, Drama" value="{{ old('new_movie_genre') }}">
                    </div>

                    <div class="form-group">
                        <label for="char_character_name" class="form-label">Character Name <span class="required-star">*</span></label>
                        <input type="text" id="char_character_name" name="character_name" class="form-input" placeholder="e.g. Joko" required value="{{ old('character_name') }}">
                    </div>
                </div>

                <div class="form-actions" style="margin-top: 20px;">
                    <button type="submit" class="btn-primary">Add Filmography Role</button>
                </div>
            </form>

            <div class="table-responsive">
                <table class="camp-table">
                    <thead>
                        <tr>
                            <th>Movie</th>
                            <th>Character</th>
                            <th class="col-actions">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($actor->characters as $character)
                            <tr>
                                <td>
                                    <strong>{{ $character->movie->title ?? 'Unknown' }}</strong>
                                    @if($character->movie && $character->movie->release_year)
                                        <span class="label-hint">({{ $character->movie->release_year }})</span>
                                    @endif
                                </td>
                                <td>{{ $character->character_name }}</td>
                                <td class="col-actions">
                                    <form method="POST" action="{{ route('camp.characters.destroy', [$actor, $character]) }}" style="display: inline;">
                                        @csrf
                                        @method('DELETE')
                                        <button type="submit" class="btn-action btn-delete">Delete</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr>
                                <td colspan="3" class="table-empty-state">No filmography roles recorded yet.</td>
                            </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Section 2: Live Recognition Title Keywords (actor_roles table) -->
        <section class="camp-form-card">
            <h2 class="card-section-title">Live Recognition Title Keywords</h2>
            <p class="section-desc">Matches keywords in active video player or browser tab titles during live recognition to display the actor's active character badge (e.g. Role: Bagas).</p>

            <form method="POST" action="{{ route('camp.roles.store', $actor) }}" style="margin-bottom: 24px;">
                @csrf

                <div class="form-grid">
                    <div class="form-group">
                        <label for="movie_keywords" class="form-label">Movie / Title Keywords <span class="required-star">*</span> <span class="label-hint">(comma-separated, lowercase)</span></label>
                        <input type="text" id="movie_keywords" name="movie_keywords" class="form-input" placeholder="e.g. yowis ben, lara ati" required value="{{ old('movie_keywords') }}">
                    </div>

                    <div class="form-group">
                        <label for="role_character_name" class="form-label">Displayed Character Name <span class="required-star">*</span></label>
                        <input type="text" id="role_character_name" name="character_name" class="form-input" placeholder="e.g. Bayu" required value="{{ old('character_name') }}">
                    </div>
                </div>

                <div class="form-actions" style="margin-top: 20px;">
                    <button type="submit" class="btn-primary">Add Recognition Keyword</button>
                </div>
            </form>

            <div class="table-responsive" style="margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.08);">
                <table class="camp-table">
                    <thead>
                        <tr>
                            <th>Movie / Title Keywords</th>
                            <th>Character</th>
                            <th class="col-actions">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($actor->roles as $role)
                            <tr>
                                <td><code>{{ $role->movie_keywords }}</code></td>
                                <td>{{ $role->character_name }}</td>
                                <td class="col-actions">
                                    <form method="POST" action="{{ route('camp.roles.destroy', [$actor, $role]) }}" style="display: inline;">
                                        @csrf
                                        @method('DELETE')
                                        <button type="submit" class="btn-action btn-delete">Delete</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr>
                                <td colspan="3" class="table-empty-state">No recognition role keywords saved yet.</td>
                            </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </section>

    </div>

</div>
@endsection
