<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Character;

class CharacterSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $characters = [
            [
                'id' => 1,
                'actor_id' => 1,
                'movie_id' => 1,
                'character_name' => 'Dilan',
                'recognition_label' => 'Dilan',
            ],
            [
                'id' => 2,
                'actor_id' => 2,
                'movie_id' => 2,
                'character_name' => 'B.J. Habibie',
                'recognition_label' => 'Habibie',
            ],
            [
                'id' => 3,
                'actor_id' => 3,
                'movie_id' => 3,
                'character_name' => 'Jaka',
                'recognition_label' => 'Jaka',
            ],
            [
                'id' => 4,
                'actor_id' => 4,
                'movie_id' => 4,
                'character_name' => 'Hayati',
                'recognition_label' => 'Hayati',
            ],
            [
                'id' => 5,
                'actor_id' => 5,
                'movie_id' => 5,
                'character_name' => 'Hardo',
                'recognition_label' => 'Hardo',
            ],
        ];

        foreach ($characters as $charData) {
            Character::updateOrCreate(['id' => $charData['id']], $charData);
        }
    }
}
