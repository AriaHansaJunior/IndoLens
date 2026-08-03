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
                'age' => 31,
                'nationality' => 'Malang, Jawa Timur', // Note: User requested Tempat Lahir, storing in nationality for now
                'height' => '170 cm',
                'occupation' => 'Actor, Director, Comedian',
                'photo' => 'bayu_skak.png',
                'summary' => 'Bayu Eko Moektito, lebih dikenal sebagai Bayu Skak, adalah seorang aktor, sutradara, komedian, dan YouTuber Indonesia. Ia dikenal luas berkat perannya dalam seri film Yowis Ben dan Sekawan Limo.',
            ]
        ];

        foreach ($actors as $actorData) {
            Actor::updateOrCreate(['id' => $actorData['id']], $actorData);
        }
    }
}
