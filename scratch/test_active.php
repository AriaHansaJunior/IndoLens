<?php
require __DIR__ . '/../vendor/autoload.php';
$app = require_once __DIR__ . '/../bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

$controller = new App\Http\Controllers\ActiveActorController();
$request = Illuminate\Http\Request::create(
    '/api/actors/active',
    'POST',
    [],
    [],
    [],
    ['CONTENT_TYPE' => 'application/json'],
    json_encode(['actors' => ['Bayu Eko Moektito'], 'window_title' => 'Sekawan Limo'])
);

$res = $controller->updateActive($request);
echo "Response: " . $res->getContent() . "\n";

$detected = App\Models\Actor::where('is_detected', true)->get();
echo "Detected count in DB: " . $detected->count() . "\n";
foreach ($detected as $a) {
    echo " - ID {$a->id}: {$a->full_name} | Role: {$a->current_character_name}\n";
}
