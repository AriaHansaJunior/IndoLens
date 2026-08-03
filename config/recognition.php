<?php

return [

    'max_video_size' => 51200, // In kilobytes (50 MB)

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

];
