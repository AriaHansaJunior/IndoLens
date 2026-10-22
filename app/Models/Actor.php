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

    /**
     * Get the accessible public URL for the actor's profile photo.
     */
    public function getPhotoUrlAttribute(): string
    {
        if (!empty($this->photo)) {
            if (str_starts_with($this->photo, 'http://') || str_starts_with($this->photo, 'https://')) {
                return $this->photo;
            }
            if (\Illuminate\Support\Facades\Storage::disk('public')->exists($this->photo)) {
                return asset('storage/' . $this->photo);
            }
            if (\Illuminate\Support\Facades\Storage::disk('public')->exists('actors/' . $this->photo)) {
                return asset('storage/actors/' . $this->photo);
            }
        }

        $firstImage = $this->images()->first();
        if ($firstImage && \Illuminate\Support\Facades\Storage::disk('public')->exists($firstImage->image)) {
            return asset('storage/' . $firstImage->image);
        }

        return 'https://ui-avatars.com/api/?name=' . urlencode($this->full_name) . '&background=0D1321&color=165DFF&size=400';
    }
}
