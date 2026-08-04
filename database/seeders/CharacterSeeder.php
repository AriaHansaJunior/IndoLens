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
                'character_name' => 'Bayu',
            ],
            [
                'id' => 2,
                'actor_id' => 1,
                'movie_id' => 2,
                'character_name' => 'Bagus',
            ]
        ];

        foreach ($characters as $data) {
            Character::updateOrCreate(['id' => $data['id']], $data);
        }
    }
}
