<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class HomeController extends Controller
{
    /**
     * Display the main IndoLens interface.
     */
    public function index()
    {
        $currentVideoUrl = session('current_video_url');
        $recognitionData = session('recognition_data');

        // If no active video uploaded in session, clear stale recognized actor names
        if (empty($currentVideoUrl)) {
            session()->forget('recognized_actor_names');
            session()->forget('recognition_data');
        }

        $hasActiveVideo = !empty($currentVideoUrl);

        return view('home', compact('currentVideoUrl', 'recognitionData', 'hasActiveVideo'));
    }
}
