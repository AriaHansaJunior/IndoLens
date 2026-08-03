<?php

namespace App\Http\Controllers;

use App\Models\Actor;
use App\Services\ActorService;
use Illuminate\Http\Request;

class ActorController extends Controller
{
    protected ActorService $actorService;

    public function __construct(ActorService $actorService)
    {
        $this->actorService = $actorService;
    }

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
        $actor = $this->getActor($id);
        
        // As per requirement, determine movie context if available, otherwise null
        $movieContext = session('recognized_movie_id', null);
        
        $character = $this->getCharacter($actor, $movieContext);
        $movies = $this->getFilmography($actor);

        return view('actors.show', compact('actor', 'character', 'movies'));
    }

    /**
     * Reserved method to get Actor model via Service.
     */
    protected function getActor(string $id): Actor
    {
        return $this->actorService->getActorDetail($id);
    }

    /**
     * Reserved method to get Character model via Service.
     */
    protected function getCharacter(Actor $actor, $movie = null)
    {
        return $this->actorService->getCharacter($actor, $movie);
    }

    /**
     * Reserved method to get Filmography via Service.
     */
    protected function getFilmography(Actor $actor)
    {
        return $this->actorService->getMovies($actor);
    }
}
