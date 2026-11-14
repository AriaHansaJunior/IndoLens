<?php

namespace App\Models;

use App\Traits\HasUuid;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class Movie extends Model
{
    use HasFactory, HasUuid;

    protected $fillable = [
        'uuid',
        'title',
        'release_year',
        'genre',
        'poster',
        'synopsis',
        'description',
    ];

    /**
     * Get characters appearing in the movie.
     */
    public function characters(): HasMany
    {
        return $this->hasMany(Character::class, 'movie_id');
    }

    /**
     * Get actors cast in the movie via the characters table.
     */
    public function actors(): BelongsToMany
    {
        return $this->belongsToMany(Actor::class, 'characters')
            ->withPivot('character_name')
            ->withTimestamps();
    }
}
