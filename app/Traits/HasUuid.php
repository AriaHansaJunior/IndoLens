<?php

namespace App\Traits;

use Illuminate\Support\Str;

trait HasUuid
{
    /**
     * Initialize a default UUID for new model instances (works even if model events are muted).
     */
    protected function initializeHasUuid(): void
    {
        if (!$this->exists && empty($this->attributes['uuid'])) {
            $this->attributes['uuid'] = (string) Str::uuid();
        }
    }

    /**
     * Automatically assign a UUID when creating a model record.
     */
    protected static function bootHasUuid(): void
    {
        static::creating(function ($model) {
            if (empty($model->uuid)) {
                $model->uuid = (string) Str::uuid();
            }
        });
    }

    /**
     * Use UUID instead of sequential integer ID in public URLs.
     */
    public function getRouteKeyName(): string
    {
        return 'uuid';
    }
}
