<?php

namespace App\Services;

use App\Models\Actor;
use App\Models\Movie;
use App\Models\Character;
use Illuminate\Support\Collection;

class ActorService
{
    /**
     * Get actor detail by ID.
     */
    public function getActorDetail($id): Actor
    {
        return Actor::with('characters.movie')->findOrFail($id);
    }

    /**
     * Get character name for an actor, optionally filtered by movie.
     */
    public function getCharacter(Actor $actor, $movie = null): ?Character
    {
        // If a specific movie ID is provided (e.g., from recognition session), filter by it.
        if ($movie) {
            return $actor->characters()->where('movie_id', $movie)->first();
        }
        
        // Otherwise return the first associated character
        return $actor->characters()->first();
    }

    /**
     * Get filmography (movies) for the actor, ordered by release year.
     */
    public function getMovies(Actor $actor): Collection
    {
        // Assuming movies are linked through character relationships or filmography pivot
        // Based on Session 11 blueprint, we use 'characters -> movies' relation
        $movies = $actor->characters->map(function ($character) {
            return $character->movie;
        })->filter()->unique('id');

        // Sort DESC by release_year
        return $movies->sortByDesc('release_year')->values();
    }
}
