<?php

namespace App\Services;

use App\Models\Actor;
use App\Models\Character;
use App\Models\Movie;
use Illuminate\Support\Collection;

class ActorService
{
    /**
     * Get actor detail by ID with characters and aliases.
     */
    public function getActorDetail($id): Actor
    {
        return Actor::with(['characters', 'aliases', 'images'])->findOrFail($id);
    }

    /**
     * Get character played by an actor.
     */
    public function getCharacter(Actor $actor, $movieTitle = null): ?Character
    {
        if ($movieTitle) {
            return Character::where('actor_name', $actor->full_name)
                ->where('movie_title', $movieTitle)
                ->first();
        }

        return Character::where('actor_name', $actor->full_name)->first();
    }

    /**
     * Get filmography movies associated with the actor.
     */
    public function getMovies(Actor $actor): Collection
    {
        $movieTitles = Character::where('actor_name', $actor->full_name)
            ->pluck('movie_title');

        return Movie::whereIn('title', $movieTitles)->get();
    }
}
