<?php

namespace App\Services;

use App\Models\Actor;
use App\Models\Character;
use App\Models\Movie;
use Illuminate\Support\Collection;

class ActorService
{
    /**
     * Get actor detail by ID with characters and associated movie.
     */
    public function getActorDetail($id): Actor
    {
        return Actor::with(['characters.movie'])->findOrFail($id);
    }

    /**
     * Get character played by an actor.
     */
    public function getCharacter(Actor $actor, $movieId = null): ?Character
    {
        if ($movieId) {
            return Character::where('actor_id', $actor->id)
                ->where('movie_id', $movieId)
                ->first();
        }

        return Character::where('actor_id', $actor->id)->first();
    }

    /**
     * Get filmography movies associated with the actor.
     */
    public function getMovies(Actor $actor): Collection
    {
        $movieIds = Character::where('actor_id', $actor->id)
            ->pluck('movie_id');

        return Movie::whereIn('id', $movieIds)->get();
    }
}
