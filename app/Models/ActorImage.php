<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ActorImage extends Model
{
    use HasFactory;

    protected $fillable = [
        'actor_name',
        'image',
    ];

    /**
     * Get associated actor model.
     */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(Actor::class, 'actor_name', 'full_name');
    }
}
