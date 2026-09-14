<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>IndoLens — Indonesian Actor Recognition System</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

    @vite(['resources/css/app.css', 'resources/js/app.js'])
    @yield('assets')
</head>
<body>

    <div class="app-container">
        <!-- App Header -->
        <header class="app-header">
            <div class="header-left">
                <a href="/" class="brand-logo-link" title="IndoLens — Indonesian Actor Recognition System">
                    <div class="logo-badge">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 7V5a2 2 0 0 1 2-2h2"/>
                            <path d="M17 3h2a2 2 0 0 1 2 2v2"/>
                            <path d="M21 17v2a2 2 0 0 1-2 2h-2"/>
                            <path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
                            <circle cx="12" cy="12" r="3.5" fill="currentColor" fill-opacity="0.25"/>
                            <circle cx="12" cy="12" r="6"/>
                        </svg>
                    </div>
                    <span class="brand-name">IndoLens</span>
                </a>

                <!-- Navigation Links -->
                <nav class="app-nav">
                    <a href="{{ route('actors.index') }}" class="nav-link {{ request()->routeIs('actors.*') || request()->is('/') ? 'active' : '' }}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                            <circle cx="9" cy="7" r="4"/>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                        </svg>
                        <span>Actors</span>
                    </a>
                    <a href="{{ route('camera.index') }}" class="nav-link {{ request()->routeIs('camera.*') ? 'active' : '' }}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                            <circle cx="12" cy="13" r="4"/>
                        </svg>
                        <span>Camera</span>
                    </a>
                    <a href="{{ route('camp.index') }}" class="nav-link {{ request()->routeIs('camp.*') ? 'active' : '' }}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 21h18M3 7v14M21 7v14M6 7V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v3M9 11v6M15 11v6"/>
                        </svg>
                        <span>Camp</span>
                    </a>
                </nav>
            </div>

            <!-- Author Identity -->
            <div class="author-badge">
                <div class="author-info">
                    <span class="author-nim">160423037</span>
                    <span class="author-separator">•</span>
                    <span class="author-name">Aria Hansa Junior</span>
                </div>
                <div class="author-avatar-wrapper">
                    <img src="{{ asset('img/foto Aria Hansa Junior.jpg') }}" alt="Aria Hansa Junior" class="author-avatar" onerror="this.src='https://ui-avatars.com/api/?name=Aria+Hansa+Junior&background=165DFF&color=ffffff&size=100'">
                </div>
            </div>
        </header>

        <!-- Main View Content -->
        <main class="main-content">
            @yield('content')
        </main>
    </div>

    <!-- Toast Notifications Container -->
    <div id="toastContainer" class="toast-container"></div>

</body>
</html>
