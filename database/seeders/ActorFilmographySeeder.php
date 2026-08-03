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
            ['id' => 2, 'actor_id' => 1, 'movie_id' => 2],
        ];

        foreach ($filmographies as $filmographyData) {
            ActorFilmography::updateOrCreate(['id' => $filmographyData['id']], $filmographyData);
        }
    }
}
