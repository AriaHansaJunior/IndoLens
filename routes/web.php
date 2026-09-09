<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ActorController;
use App\Http\Controllers\CameraController;

Route::get('/', [ActorController::class, 'index'])->name('actors.index');
Route::get('/actors', [ActorController::class, 'index']);
Route::get('/actors/{id}', [ActorController::class, 'show'])->name('actors.show');

// Camera Capture route (Session 1)
Route::get('/camera', [CameraController::class, 'index'])->name('camera.index');

// Real-time integration API
use App\Http\Controllers\ActiveActorController;
Route::post('/api/actors/active', [ActiveActorController::class, 'updateActive']);
Route::get('/api/actors/active', [ActiveActorController::class, 'getActive']);

// Proxy YOLO API requests directly via Laravel (Session 3)
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

Route::post('/api/yolo/detect', function (Request $request) {
    try {
        $response = Http::withBody($request->getContent(), 'image/jpeg')
            ->post('http://127.0.0.1:8002/detect');
            
        return response($response->body(), $response->status())
            ->header('Content-Type', 'application/json');
    } catch (\Exception $e) {
        return response()->json([
            'status' => 'error',
            'message' => 'YOLO service is not reachable on port 8002'
        ], 502);
    }
});
