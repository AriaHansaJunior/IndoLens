<?php

namespace Database\Seeders;

use App\Models\Actor;
use App\Models\Character;
use App\Models\Movie;
use Illuminate\Database\Seeder;

class CharacterSeeder extends Seeder
{
    /**
     * Menghubungkan seluruh 12 aktor dengan filmografi dan nama peran karakter masing-masing di tabel characters.
     */
    public function run(): void
    {
        $mapping = [
            ['actor' => 'Bayu Eko Moektito',   'movie' => 'Yowis Ben',                                  'year' => 2018, 'role' => 'Bayu'],
            ['actor' => 'Bayu Eko Moektito',   'movie' => 'Sekawan Limo',                               'year' => 2024, 'role' => 'Bagas'],
            ['actor' => 'Alice Norin',         'movie' => 'Psikopat',                                   'year' => 2005, 'role' => 'Mita'],
            ['actor' => 'Alice Norin',         'movie' => 'Ketika Cinta Bertasbih',                     'year' => 2009, 'role' => 'Eliana'],
            ['actor' => 'Alice Norin',         'movie' => 'Kutuk',                                      'year' => 2019, 'role' => 'Elena'],
            ['actor' => 'Angga Aldi Yunanda',  'movie' => 'Dua Garis Biru',                             'year' => 2019, 'role' => 'Bima'],
            ['actor' => 'Angga Aldi Yunanda',  'movie' => 'Cinta Pertama, Kedua & Ketiga',              'year' => 2021, 'role' => 'Raja'],
            ['actor' => 'Angga Aldi Yunanda',  'movie' => 'My Annoying Brother',                        'year' => 2024, 'role' => 'Kemal'],
            ['actor' => 'Ario Bayu',           'movie' => 'Laskar Pelangi',                             'year' => 2008, 'role' => 'Lintang Dewasa'],
            ['actor' => 'Ario Bayu',           'movie' => 'Soekarno: Indonesia Merdeka',                'year' => 2013, 'role' => 'Soekarno'],
            ['actor' => 'Ario Bayu',           'movie' => 'Gundala',                                    'year' => 2019, 'role' => 'Ghazul'],
            ['actor' => 'Babe Cabita',         'movie' => 'Comic 8',                                    'year' => 2014, 'role' => 'Babe Cabita'],
            ['actor' => 'Babe Cabita',         'movie' => 'Aku, Kau & KUA',                             'year' => 2014, 'role' => 'Pepi'],
            ['actor' => 'Babe Cabita',         'movie' => 'The Underdogs',                              'year' => 2017, 'role' => 'Nanang'],
            ['actor' => 'Bunga Citra Lestari', 'movie' => 'Habibie & Ainun',                            'year' => 2012, 'role' => 'Hasri Ainun Besari'],
            ['actor' => 'Bunga Citra Lestari', 'movie' => 'My Stupid Boss',                             'year' => 2016, 'role' => 'Diana'],
            ['actor' => 'Bunga Citra Lestari', 'movie' => '3 Srikandi',                                 'year' => 2016, 'role' => 'Nurfitriyana Saiman'],
            ['actor' => 'Chelsea Islan',       'movie' => 'Merry Riana: Mimpi Sejuta Dolar',            'year' => 2014, 'role' => 'Merry Riana'],
            ['actor' => 'Chelsea Islan',       'movie' => 'Guru Bangsa: Tjokroaminoto',                 'year' => 2015, 'role' => 'Stella Almira'],
            ['actor' => 'Chelsea Islan',       'movie' => 'Ayat-Ayat Cinta 2',                          'year' => 2017, 'role' => 'Keira'],
            ['actor' => 'Darius Sinathrya',    'movie' => 'Merah Putih',                                'year' => 2009, 'role' => 'Marius'],
            ['actor' => 'Darius Sinathrya',    'movie' => 'Dilema',                                     'year' => 2012, 'role' => 'Boy'],
            ['actor' => 'Darius Sinathrya',    'movie' => 'Surga yang Tak Dirindukan 3',                'year' => 2021, 'role' => 'Amran'],
            ['actor' => 'Deva Mahenra',        'movie' => 'Sabtu Bersama Bapak',                        'year' => 2016, 'role' => 'Cakra'],
            ['actor' => 'Deva Mahenra',        'movie' => 'Ghost Writer',                               'year' => 2019, 'role' => 'Vino'],
            ['actor' => 'Deva Mahenra',        'movie' => 'Ipar Adalah Maut',                           'year' => 2024, 'role' => 'Aris'],
            ['actor' => 'Dian Sastrowardoyo',  'movie' => 'Ada Apa dengan Cinta?',                      'year' => 2002, 'role' => 'Cinta'],
            ['actor' => 'Dian Sastrowardoyo',  'movie' => 'Kartini',                                    'year' => 2017, 'role' => 'Raden Adjeng Kartini'],
            ['actor' => 'Dian Sastrowardoyo',  'movie' => 'Aruna dan Lidahnya',                         'year' => 2018, 'role' => 'Aruna'],
            ['actor' => 'Dinda Kanyadewi',     'movie' => 'Kawin Kontrak',                              'year' => 2008, 'role' => 'Isa'],
            ['actor' => 'Dinda Kanyadewi',     'movie' => 'Milly & Mamet: Ini Bukan Cinta & Rangga',    'year' => 2018, 'role' => 'Lela'],
            ['actor' => 'Dinda Kanyadewi',     'movie' => 'Badarawuhi di Desa Penari',                  'year' => 2024, 'role' => 'Jiyanti'],
            ['actor' => 'Dodit Mulyanto',      'movie' => 'Cek Toko Sebelah',                           'year' => 2016, 'role' => 'Kuncoro'],
            ['actor' => 'Dodit Mulyanto',      'movie' => 'Susah Sinyal',                               'year' => 2017, 'role' => 'Ngatno'],
            ['actor' => 'Dodit Mulyanto',      'movie' => 'Rumah Dinas Bapak',                          'year' => 2024, 'role' => 'Bapak (Joko)'],
        ];

        foreach ($mapping as $item) {
            $actor = Actor::where('full_name', $item['actor'])->first();
            $movie = Movie::where('title', $item['movie'])
                ->where('release_year', $item['year'])
                ->first();

            if ($actor && $movie) {
                Character::updateOrCreate(
                    ['actor_id' => $actor->id, 'movie_id' => $movie->id],
                    ['character_name' => $item['role']]
                );
            }
        }
    }
}
