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
                'title' => 'Yowis Ben',
                'release_year' => 2018,
                'poster' => 'movies/yowis_ben.jpg',
                'description' => 'A comedy film directed by Fajar Nugros and Bayu Skak.',
            ],
            [
                'id' => 2,
                'title' => 'Sekawan Limo',
                'release_year' => 2024,
                'poster' => 'movies/sekawan_limo.jpg',
                'description' => 'A comedy horror film directed by Bayu Skak.',
            ],
        ];

        foreach ($movies as $movieData) {
            Movie::updateOrCreate(['id' => $movieData['id']], $movieData);
        }
    }
}
