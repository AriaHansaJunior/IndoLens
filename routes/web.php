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

use App\Http\Controllers\CampController;

// Camp Administration Routes (Session 6)
Route::get('/camp', [CampController::class, 'index'])->name('camp.index');
Route::get('/camp/create', [CampController::class, 'create'])->name('camp.create');
Route::post('/camp', [CampController::class, 'store'])->name('camp.store');
Route::get('/camp/{id}/edit', [CampController::class, 'edit'])->name('camp.edit');
Route::put('/camp/{id}', [CampController::class, 'update'])->name('camp.update');
Route::delete('/camp/{id}', [CampController::class, 'destroy'])->name('camp.destroy');
Route::get('/camp/{id}/faces', [CampController::class, 'faces'])->name('camp.faces');
Route::post('/camp/{id}/faces', [CampController::class, 'storeFaces'])->name('camp.faces.store');
Route::delete('/camp/{actorId}/faces/{imageId}', [CampController::class, 'destroyFace'])->name('camp.faces.destroy');

// Recognition-to-Database Actor Lookup API (Session 6)
Route::get('/api/actors/lookup', [CampController::class, 'lookup'])->name('api.actors.lookup');

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

