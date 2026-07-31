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
                'award_name' => 'Indonesian Movie Actors Awards - Favorite Actor',
                'award_year' => 2018,
            ],
            [
                'id' => 2,
                'actor_id' => 2,
                'award_name' => 'Festival Film Indonesia - Best Actor',
                'award_year' => 2013,
            ],
            [
                'id' => 3,
                'actor_id' => 3,
                'award_name' => 'Indonesian Movie Actors Awards - Best Actor',
                'award_year' => 2014,
            ],
            [
                'id' => 4,
                'actor_id' => 4,
                'award_name' => 'Festival Film Bandung - Best Actress',
                'award_year' => 2014,
            ],
            [
                'id' => 5,
                'actor_id' => 5,
                'award_name' => 'Festival Film Indonesia - Best Supporting Actor',
                'award_year' => 2013,
            ],
        ];

        foreach ($awards as $awardData) {
            ActorAward::updateOrCreate(['id' => $awardData['id']], $awardData);
        }
    }
}
