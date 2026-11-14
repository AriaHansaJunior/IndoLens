<?php

namespace App\Models;

use App\Traits\HasUuid;
use Illuminate\Database\Eloquent\Model;

class ActorRole extends Model
{
    use HasUuid;

    protected $fillable = ['uuid', 'actor_id', 'movie_keywords', 'character_name'];

    public function actor()
    {
        return $this->belongsTo(Actor::class);
    }
}
