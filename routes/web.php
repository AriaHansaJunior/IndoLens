<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\HomeController;
use App\Http\Controllers\RecognitionController;
use App\Http\Controllers\ActorController;

Route::get('/', [HomeController::class, 'index']);
Route::post('/upload', [RecognitionController::class, 'upload']);
Route::get('/actors', [ActorController::class, 'index']);
Route::get('/actors/{id}', [ActorController::class, 'show']);
