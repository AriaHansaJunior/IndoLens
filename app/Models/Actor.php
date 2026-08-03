<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Actor extends Model
{
    use HasFactory;

    protected $fillable = [
        'full_name',
        'birth_date',
        'birth_place',
        'age',
        'gender',
        'photo',
        'biography',
        'instagram',
        'wikipedia',
        'imdb',
    ];

    /**
     * Get characters played by the actor.
     */
    public function characters(): HasMany
    {
        return $this->hasMany(Character::class, 'actor_name', 'full_name');
    }

    /**
     * Get aliases for the actor.
     */
    public function aliases(): HasMany
    {
        return $this->hasMany(ActorAlias::class, 'actor_name', 'full_name');
    }

    /**
     * Get FaceNet dataset images for the actor.
     */
    public function images(): HasMany
    {
        return $this->hasMany(ActorImage::class, 'actor_name', 'full_name');
    }
}
