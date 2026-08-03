<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\ActorAlias;

class ActorAliasSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $aliases = [
            [
                'id' => 1,
                'actor_name' => 'Bayu Skak',
                'alias' => 'Bayu Eko Moektito',
            ]
        ];

        foreach ($aliases as $data) {
            ActorAlias::updateOrCreate(['id' => $data['id']], $data);
        }
    }
}
