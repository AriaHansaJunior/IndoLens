<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\ActorImage;

class ActorImageSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $images = [
            [
                'id' => 1,
                'actor_name' => 'Bayu Skak',
                'image' => 'bayu_skak_01.jpg',
            ]
        ];

        foreach ($images as $data) {
            ActorImage::updateOrCreate(['id' => $data['id']], $data);
        }
    }
}
