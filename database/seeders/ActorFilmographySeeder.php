<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\ActorFilmography;

class ActorFilmographySeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $filmographies = [
            ['id' => 1, 'actor_id' => 1, 'movie_id' => 1],
            ['id' => 2, 'actor_id' => 2, 'movie_id' => 2],
            ['id' => 3, 'actor_id' => 3, 'movie_id' => 3],
            ['id' => 4, 'actor_id' => 4, 'movie_id' => 4],
            ['id' => 5, 'actor_id' => 5, 'movie_id' => 5],
        ];

        foreach ($filmographies as $filmographyData) {
            ActorFilmography::updateOrCreate(['id' => $filmographyData['id']], $filmographyData);
        }
    }
}
