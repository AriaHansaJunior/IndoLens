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
        return $this->hasMany(Character::class, 'actor_id');
    }
}
