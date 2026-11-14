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
     * Display a listing of all actors.
     */
    public function index()
    {
        $actors = Actor::with(['images'])
            ->orderBy('is_detected', 'desc')
            ->orderBy('full_name', 'asc')
            ->get();

        return view('actors.index', [
            'actors' => $actors,
            'status' => 'Known',
        ]);
    }

    /**
     * Display the specified actor.
     */
    public function show(Actor $actor)
    {
        $actor  = $this->actorService->getActorDetail($actor);
        $movies = $this->getFilmography($actor);

        return view('actors.show', compact('actor', 'movies'));
    }

    /**
     * Reserved method to get Actor model via Service.
     */
    protected function getActor(Actor|string $actor): Actor
    {
        return $this->actorService->getActorDetail($actor);
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
