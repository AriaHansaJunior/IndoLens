<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ActorAlias extends Model
{
    use HasFactory;

    protected $fillable = [
        'actor_name',
        'alias',
    ];

    /**
     * Get associated actor model.
     */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(Actor::class, 'actor_name', 'full_name');
    }
}
