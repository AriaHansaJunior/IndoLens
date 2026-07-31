<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;

class Actor extends Model
{
    use HasFactory;

    protected $fillable = [
        'full_name',
        'birth_date',
        'age',
        'nationality',
        'height',
        'occupation',
        'photo',
        'summary',
    ];

    /**
     * Get characters played by the actor.
     */
    public function characters(): HasMany
    {
        return $this->hasMany(Character::class);
    }

    /**
     * Get awards received by the actor.
     */
    public function awards(): HasMany
    {
        return $this->hasMany(ActorAward::class);
    }

    /**
     * Get filmography pivot records for the actor.
     */
    public function filmographies(): HasMany
    {
        return $this->hasMany(ActorFilmography::class);
    }

    /**
     * Get movies associated with the actor.
     */
    public function movies(): BelongsToMany
    {
        return $this->belongsToMany(Movie::class, 'actor_filmographies');
    }
}
