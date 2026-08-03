<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\ActorAward;

class ActorAwardSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $awards = [
            [
                'id' => 1,
                'actor_id' => 1,
                'award_name' => 'Piala Citra - Nominasi Penulis Skenario Asli Terbaik',
                'award_year' => 2018,
            ],
            [
                'id' => 2,
                'actor_id' => 1,
                'award_name' => 'Piala Maya - Nominasi Sutradara Pendatang Baru Terpilih',
                'award_year' => 2019,
            ],
        ];

        foreach ($awards as $awardData) {
            ActorAward::updateOrCreate(['id' => $awardData['id']], $awardData);
        }
    }
}
