<?php

namespace Database\Seeders;

use Carbon\Carbon;
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
                'full_name' => 'Bayu Eko Moektito',
                'birth_date' => '1993-11-13',
                'birth_place' => 'Malang, Jawa Timur',
                'age' => Carbon::parse('1993-11-13')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/1-bayu-eko-moektito/profile-bayu-eko-moektito.jpg',
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
