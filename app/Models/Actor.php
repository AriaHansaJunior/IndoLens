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
        'is_detected',
        'current_character_name',
        'detected_window_title',
    ];

    /**
     * Get characters played by the actor (legacy).
     */
    public function characters(): HasMany
    {
        return $this->hasMany(Character::class, 'actor_id');
    }

    /**
     * Get the movie roles (character per film) for this actor.
     */
    public function roles(): HasMany
    {
        return $this->hasMany(ActorRole::class, 'actor_id');
    }

    /**
     * Get the multiple face images for this actor.
     */
    public function images(): HasMany
    {
        return $this->hasMany(ActorImage::class, 'actor_id');
    }

    /**
     * Get English label for gender to maintain English UI standard.
     */
    public function getGenderLabelAttribute(): string
    {
        return match (strtolower(trim((string)$this->gender))) {
            'laki-laki', 'male' => 'Male',
            'perempuan', 'female' => 'Female',
            default => $this->gender ?: '-'
        };
    }
}
