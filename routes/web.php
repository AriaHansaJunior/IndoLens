<?php

use App\Http\Controllers\ActiveActorController;
use App\Http\Controllers\ActorController;
use App\Http\Controllers\CameraController;
use App\Http\Controllers\CampController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Route;

// Public Actor Catalog & Detail Routes
Route::get('/', [ActorController::class, 'index'])->name('actors.index');
Route::get('/actors', [ActorController::class, 'index']);
Route::get('/actors/{actor}', [ActorController::class, 'show'])->name('actors.show');

// Live Camera Stream Route
Route::get('/camera', [CameraController::class, 'index'])->name('camera.index');

// Real-time Recognition API
Route::post('/api/actors/active', [ActiveActorController::class, 'updateActive']);
Route::get('/api/actors/active', [ActiveActorController::class, 'getActive']);
Route::get('/api/actors/lookup', [CampController::class, 'lookup'])->name('api.actors.lookup');

// Camp Database Administration Routes (UUID Route Key Binding)
Route::prefix('camp')->name('camp.')->group(function () {
    Route::get('/', [CampController::class, 'index'])->name('index');
    Route::get('/create', [CampController::class, 'create'])->name('create');
    Route::post('/', [CampController::class, 'store'])->name('store');
    Route::get('/{actor}/edit', [CampController::class, 'edit'])->name('edit');
    Route::put('/{actor}', [CampController::class, 'update'])->name('update');
    Route::delete('/{actor}', [CampController::class, 'destroy'])->name('destroy');

    Route::get('/{actor}/faces', [CampController::class, 'faces'])->name('faces');
    Route::post('/{actor}/faces', [CampController::class, 'storeFaces'])->name('faces.store');
    Route::delete('/{actor}/faces', [CampController::class, 'destroyMultipleFaces'])->name('faces.destroy-multiple');
    Route::delete('/{actor}/faces/{actorImage}', [CampController::class, 'destroyFace'])->name('faces.destroy');

    Route::get('/{actor}/roles', [CampController::class, 'roles'])->name('roles');
    Route::post('/{actor}/characters', [CampController::class, 'storeCharacter'])->name('characters.store');
    Route::delete('/{actor}/characters/{character}', [CampController::class, 'destroyCharacter'])->name('characters.destroy');
    Route::post('/{actor}/roles', [CampController::class, 'storeRole'])->name('roles.store');
    Route::delete('/{actor}/roles/{actorRole}', [CampController::class, 'destroyRole'])->name('roles.destroy');
});

// Python YOLO + FaceNet Proxy Fallback
Route::post('/api/yolo/detect', function (Request $request) {
    $yoloUrl = rtrim(config('recognition.yolo_service_url', 'http://127.0.0.1:8002'), '/');

    try {
        $response = Http::timeout(15)
            ->withBody($request->getContent(), 'image/jpeg')
            ->post("{$yoloUrl}/detect");

        return response($response->body(), $response->status())
            ->header('Content-Type', 'application/json');
    } catch (\Throwable $e) {
        return response()->json([
            'status' => 'error',
            'message' => 'YOLO service is not reachable.',
        ], 502);
    }
});
