<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class CameraController extends Controller
{
    /**
     * Display the live camera capture interface.
     */
    public function index()
    {
        return view('camera.index');
    }
}
