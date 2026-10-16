<?php
require 'vendor/autoload.php';
$app = require_once 'bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

$actors = App\Models\Actor::with('images')->get();
echo "ACTORS COUNT: " . $actors->count() . PHP_EOL;
foreach ($actors as $a) {
    echo "ID: {$a->id} | Name: {$a->full_name} | Images count: " . $a->images->count() . PHP_EOL;
    foreach ($a->images as $img) {
        $path = storage_path('app/public/' . $img->image);
        $exists = file_exists($path) ? 'EXISTS' : 'NOT FOUND';
        echo "   -> Img ID: {$img->id} | File: {$img->image} | Disk: {$exists}" . PHP_EOL;
    }
}
