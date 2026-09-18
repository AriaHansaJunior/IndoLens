<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Actor;
use App\Models\ActorRole;

class ActorRoleSeeder extends Seeder
{
    /**
     * Seed actor roles for character name mapping.
     * movie_keywords is a comma-separated list of keywords to match against the window title.
     * Matching is case-insensitive.
     */
    public function run(): void
    {
        $bayuActor = Actor::where('full_name', 'Bayu Eko Moektito')->orWhere('id', 1)->first();

        if ($bayuActor) {
            $roles = [
                ['movie_keywords' => 'yowis ben',        'character_name' => 'Bayu'],
                ['movie_keywords' => 'sekawan limo',     'character_name' => 'Bagas'],
            ];

            foreach ($roles as $role) {
                ActorRole::firstOrCreate(
                    ['actor_id' => $bayuActor->id, 'movie_keywords' => $role['movie_keywords']],
                    ['character_name' => $role['character_name']]
                );
            }
        }
    }
}
