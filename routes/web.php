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
