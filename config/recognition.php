<?php

return [
    'max_video_size' => 1048576, // In kilobytes (1024 MB = 1 GB)

    'allowed_extensions' => [
        'mp4',
        'avi',
        'mov',
        'mkv',
    ],

    'temporary_path' => storage_path('app/ai/temp'),

    'result_path' => storage_path('app/ai/results'),

    'python_entry' => base_path('python/main.py'),

    'python_binary' => 'python',

    'yolo_service_url' => env('YOLO_SERVICE_URL', 'http://127.0.0.1:8002'),

    // Process timeout in seconds. 0 = unlimited (recommended for long videos).
    'process_timeout' => 0,

];
