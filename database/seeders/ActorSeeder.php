<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Actor;

class ActorSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $actors = [
            [
                'id' => 1,
                'full_name' => 'Iqbaal Ramadhan',
                'birth_date' => '1999-12-28',
                'age' => 26,
                'nationality' => 'Indonesian',
                'height' => '175 cm',
                'occupation' => 'Actor, Musician',
                'photo' => 'actors/iqbaal_ramadhan.jpg',
                'summary' => 'Indonesian actor and musician known for playing Dilan.',
            ],
            [
                'id' => 2,
                'full_name' => 'Reza Rahadian',
                'birth_date' => '1987-03-05',
                'age' => 39,
                'nationality' => 'Indonesian',
                'height' => '177 cm',
                'occupation' => 'Actor, Director',
                'photo' => 'actors/reza_rahadian.jpg',
                'summary' => 'Acclaimed Indonesian actor renowned for his versatile biographical portrayals.',
            ],
            [
                'id' => 3,
                'full_name' => 'Joe Taslim',
                'birth_date' => '1981-06-23',
                'age' => 45,
                'nationality' => 'Indonesian',
                'height' => '178 cm',
                'occupation' => 'Actor, Martial Artist',
                'photo' => 'actors/joe_taslim.jpg',
                'summary' => 'Indonesian actor and martial artist featuring in national and international action films.',
            ],
            [
                'id' => 4,
                'full_name' => 'Pevita Pearce',
                'birth_date' => '1992-10-06',
                'age' => 33,
                'nationality' => 'Indonesian',
                'height' => '165 cm',
                'occupation' => 'Actress, Model',
                'photo' => 'actors/pevita_pearce.jpg',
                'summary' => 'Prominent Indonesian actress known for drama and action superhero roles.',
            ],
            [
                'id' => 5,
                'full_name' => 'Adipati Dolken',
                'birth_date' => '1991-08-19',
                'age' => 34,
                'nationality' => 'Indonesian',
                'height' => '177 cm',
                'occupation' => 'Actor',
                'photo' => 'actors/adipati_dolken.jpg',
                'summary' => 'Award-winning Indonesian film actor.',
            ],
        ];

        foreach ($actors as $actorData) {
            Actor::updateOrCreate(['id' => $actorData['id']], $actorData);
        }
    }
}
