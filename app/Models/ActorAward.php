<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ActorAward extends Model
{
    use HasFactory;

    protected $fillable = [
        'actor_id',
        'award_name',
        'award_year',
    ];

    /**
     * Get the actor for this award.
     */
    public function actor(): BelongsTo
    {
        return $this->belongsTo(Actor::class);
    }
}
