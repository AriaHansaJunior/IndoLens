<?php

namespace App\Http\Controllers;

use App\Models\Actor;
use Illuminate\Http\Request;

class ActorController extends Controller
{
    /**
     * Display a listing of actors that were recognized in the last video.
     */
    public function index()
    {
        $recognizedNames = session('recognized_actor_names', []);
        
        $actors = Actor::whereIn('full_name', $recognizedNames)
            ->orderBy('full_name', 'asc')
            ->get();

        return view('actors.index', [
            'actors' => $actors,
            'status' => 'Known' // Passed dynamically to Blade
        ]);
    }

    /**
     * Display the specified actor.
     */
    public function show(string $id)
    {
        $actor = Actor::findOrFail($id);
        
        // Reserved for Session 11 implementation
        return view('actors.show', compact('actor'));
    }
}
