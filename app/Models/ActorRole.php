<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ActorRole extends Model
{
    protected $fillable = ['actor_id', 'movie_keywords', 'character_name'];

    public function actor()
    {
        return $this->belongsTo(Actor::class);
    }
}
