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

    @hasSection('assets')
        @yield('assets')
    @else
        @vite(['resources/css/app.css', 'resources/js/app.js'])
    @endif
</head>
<body>

    <div class="app-container">
        <!-- App Header -->
        <header class="app-header">
            <div class="logo-badge" title="Face Detection & Recognition System">
                FD
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
