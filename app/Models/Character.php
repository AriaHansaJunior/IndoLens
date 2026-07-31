<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Character extends Model
{
    use HasFactory;

    protected $fillable = [
        'actor_id',
        'movie_id',
        'character_name',
        'recognition_label',
    ];

    /**
     * Get the actor playing this character.
     */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(Actor::class);
    }

    /**
     * Get the movie this character belongs to.
     */
    public function movie(): BelongsTo
    {
        return $this->belongsTo(Movie::class);
    }
}
