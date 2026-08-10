<!DOCTYPE html>
<html lang="id">
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
            <a href="/" class="brand-logo-link" title="IndoLens — Face Detection & Recognition System">
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
