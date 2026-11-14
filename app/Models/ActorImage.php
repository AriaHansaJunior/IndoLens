<?php

namespace App\Models;

use App\Traits\HasUuid;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ActorImage extends Model
{
    use HasFactory, HasUuid;

    protected $fillable = [
        'uuid',
        'actor_id',
        'image',
    ];

    /**
     * Get the actor that owns this face image.
     */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(Actor::class, 'actor_id');
    }
}
