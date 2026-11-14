<?php

namespace App\Services;

use App\Models\Actor;
use App\Models\Character;
use App\Models\Movie;
use Illuminate\Support\Collection;

class ActorService
{
    /**
     * Get actor detail by model, UUID, or ID with characters and associated movie.
     */
    public function getActorDetail(Actor|int|string $actor): Actor
    {
        if ($actor instanceof Actor) {
            return $actor->loadMissing(['characters.movie']);
        }

        $query = Actor::with(['characters.movie']);

        return is_numeric($actor)
            ? $query->findOrFail($actor)
            : $query->where('uuid', $actor)->firstOrFail();
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
