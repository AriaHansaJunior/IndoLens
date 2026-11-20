<?php

namespace Database\Seeders;

use App\Models\Actor;
use App\Models\ActorRole;
use Illuminate\Database\Seeder;

class ActorRoleSeeder extends Seeder
{
    /**
     * Menyimpan pemetaan kata kunci judul film ke nama karakter aktif pada tabel actor_roles untuk 12 aktor.
     */
    public function run(): void
    {
        $rolesByActor = [
            'Bayu Eko Moektito' => [
                ['movie_keywords' => 'yowis ben', 'character_name' => 'Bayu'],
                ['movie_keywords' => 'sekawan limo', 'character_name' => 'Bagas'],
            ],
            'Alice Norin' => [
                ['movie_keywords' => 'psikopat', 'character_name' => 'Mita'],
                ['movie_keywords' => 'ketika cinta bertasbih', 'character_name' => 'Eliana'],
                ['movie_keywords' => 'kutuk', 'character_name' => 'Elena'],
            ],
            'Angga Aldi Yunanda' => [
                ['movie_keywords' => 'dua garis biru', 'character_name' => 'Bima'],
                ['movie_keywords' => 'cinta pertama', 'character_name' => 'Raja'],
                ['movie_keywords' => 'my annoying brother', 'character_name' => 'Kemal'],
            ],
            'Ario Bayu' => [
                ['movie_keywords' => 'laskar pelangi', 'character_name' => 'Lintang Dewasa'],
                ['movie_keywords' => 'soekarno', 'character_name' => 'Soekarno'],
                ['movie_keywords' => 'gundala', 'character_name' => 'Ghazul'],
            ],
            'Babe Cabita' => [
                ['movie_keywords' => 'comic 8', 'character_name' => 'Babe Cabita'],
                ['movie_keywords' => 'aku, kau & kua', 'character_name' => 'Pepi'],
                ['movie_keywords' => 'the underdogs', 'character_name' => 'Nanang'],
            ],
            'Bunga Citra Lestari' => [
                ['movie_keywords' => 'habibie & ainun', 'character_name' => 'Hasri Ainun Besari'],
                ['movie_keywords' => 'my stupid boss', 'character_name' => 'Diana'],
                ['movie_keywords' => '3 srikandi', 'character_name' => 'Nurfitriyana Saiman'],
            ],
            'Chelsea Islan' => [
                ['movie_keywords' => 'merry riana', 'character_name' => 'Merry Riana'],
                ['movie_keywords' => 'tjokroaminoto', 'character_name' => 'Stella Almira'],
                ['movie_keywords' => 'ayat-ayat cinta 2', 'character_name' => 'Keira'],
            ],
            'Darius Sinathrya' => [
                ['movie_keywords' => 'merah putih', 'character_name' => 'Marius'],
                ['movie_keywords' => 'dilema', 'character_name' => 'Boy'],
                ['movie_keywords' => 'surga yang tak dirindukan 3', 'character_name' => 'Amran'],
            ],
            'Deva Mahenra' => [
                ['movie_keywords' => 'sabtu bersama bapak', 'character_name' => 'Cakra'],
                ['movie_keywords' => 'ghost writer', 'character_name' => 'Vino'],
                ['movie_keywords' => 'ipar adalah maut', 'character_name' => 'Aris'],
            ],
            'Dian Sastrowardoyo' => [
                ['movie_keywords' => 'ada apa dengan cinta', 'character_name' => 'Cinta'],
                ['movie_keywords' => 'kartini', 'character_name' => 'Raden Adjeng Kartini'],
                ['movie_keywords' => 'aruna dan lidahnya', 'character_name' => 'Aruna'],
            ],
            'Dinda Kanyadewi' => [
                ['movie_keywords' => 'kawin kontrak', 'character_name' => 'Isa'],
                ['movie_keywords' => 'milly & mamet', 'character_name' => 'Lela'],
                ['movie_keywords' => 'badarawuhi', 'character_name' => 'Jiyanti'],
            ],
            'Dodit Mulyanto' => [
                ['movie_keywords' => 'cek toko sebelah', 'character_name' => 'Kuncoro'],
                ['movie_keywords' => 'susah sinyal', 'character_name' => 'Ngatno'],
                ['movie_keywords' => 'rumah dinas bapak', 'character_name' => 'Bapak (Joko)'],
            ],
        ];

        foreach ($rolesByActor as $actorName => $roles) {
            $actor = Actor::where('full_name', $actorName)->first();
            if (!$actor) {
                continue;
            }

            foreach ($roles as $role) {
                ActorRole::firstOrCreate(
                    ['actor_id' => $actor->id, 'movie_keywords' => $role['movie_keywords']],
                    ['character_name' => $role['character_name']]
                );
            }
        }
    }
}
