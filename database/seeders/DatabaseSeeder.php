<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $this->call([
            ActorSeeder::class,
            MovieSeeder::class,
            CharacterSeeder::class,
            ActorRoleSeeder::class,
            ActorImageSeeder::class,
        ]);
    }
}
