<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\ActorImage;

class ActorImageSeeder extends Seeder
{
    /**
     * Seed Bayu Eko Moektito's 10 face reference images sequentially from ID #1.
     */
    public function run(): void
    {
        for ($i = 1; $i <= 10; $i++) {
            $imagePath = sprintf('actor-images/1-bayu-eko-moektito/bayu-eko-moektito-%02d.jpg', $i);

            ActorImage::updateOrCreate(
                ['id' => $i],
                [
                    'actor_id' => 1,
                    'image' => $imagePath,
                ]
            );
        }
    }
}
