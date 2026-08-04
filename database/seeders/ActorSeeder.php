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
                'full_name' => 'Bayu Skak',
                'birth_date' => '1993-11-13',
                'birth_place' => 'Malang, Jawa Timur',
                'age' => 31,
                'gender' => 'Laki-laki',
                'photo' => 'bayu_skak.png',
                'biography' => 'Bayu Eko Moektito, lebih dikenal sebagai Bayu Skak, adalah seorang aktor, sutradara, komedian, dan YouTuber Indonesia. Ia dikenal luas berkat perannya dalam seri film Yowis Ben dan Sekawan Limo.',
                'instagram' => 'https://www.instagram.com/moektito',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Bayu_Skak',
                'imdb' => 'https://www.imdb.com/name/nm8662914/',
            ]
        ];

        foreach ($actors as $actorData) {
            Actor::updateOrCreate(['id' => $actorData['id']], $actorData);
        }
    }
}
