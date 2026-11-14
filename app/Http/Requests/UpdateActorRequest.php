<?php

namespace App\Http\Requests;

use App\Models\Actor;

class UpdateActorRequest extends BaseActorRequest
{
    protected function ignoreActorId(): ?int
    {
        $actor = $this->route('actor') ?? $this->route('id');

        if ($actor instanceof Actor) {
            return $actor->id;
        }

        if (is_numeric($actor)) {
            return (int) $actor;
        }

        return $actor ? Actor::where('uuid', $actor)->value('id') : null;
    }
}
