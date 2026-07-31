<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Movie;

class MovieSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $movies = [
            [
                'id' => 1,
                'title' => 'Dilan 1990',
                'release_year' => 2018,
                'poster' => 'movies/dilan_1990.jpg',
                'description' => 'A romantic drama following Milea and high school student Dilan in 1990s Bandung.',
            ],
            [
                'id' => 2,
                'title' => 'Habibie & Ainun',
                'release_year' => 2012,
                'poster' => 'movies/habibie_ainun.jpg',
                'description' => 'Biographical drama portraying the life story of 3rd Indonesian President B.J. Habibie and his wife Ainun.',
            ],
            [
                'id' => 3,
                'title' => 'The Raid',
                'release_year' => 2011,
                'poster' => 'movies/the_raid.jpg',
                'description' => 'An action martial arts film detailing a SWAT team raid on an apartment building controlled by a drug lord.',
            ],
            [
                'id' => 4,
                'title' => 'Tenggelamnya Kapal Van Der Wijck',
                'release_year' => 2013,
                'poster' => 'movies/van_der_wijck.jpg',
                'description' => 'A classic romance drama adapting Buya Hamka\'s novel on cultural differences and tragedy.',
            ],
            [
                'id' => 5,
                'title' => 'Perburuan',
                'release_year' => 2019,
                'poster' => 'movies/perburuan.jpg',
                'description' => 'Historical drama based on Pramoedya Ananta Toer\'s novel depicting the PETA rebellion.',
            ],
        ];

        foreach ($movies as $movieData) {
            Movie::updateOrCreate(['id' => $movieData['id']], $movieData);
        }
    }
}
