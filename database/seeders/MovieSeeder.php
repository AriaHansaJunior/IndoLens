<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Movie;

class MovieSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $movies = [
            [
                'id' => 1,
                'title' => 'Yowis Ben',
                'release_year' => 2018,
                'genre' => 'Comedy, Music, Romance',
                'poster' => 'Yowis_Ben.jpg',
                'synopsis' => 'Bayu (Bayu Skak) menyukai Susan (Cut Meyriska) sejak lama. Namun karena dia merasa minder dengan keadaan dirinya yang pas-pasan, Bayu memutuskan memendam perasaan itu. Namun hari-hari Bayu berubah sejak Susan mengirim voice chat ke ponsel Bayu, yang membuatnya kegeeran luar biasa mengira Susan memberi isyarat agar didekati. Ternyata Susan hanya memanfaatkan Bayu untuk membantunya mensuplai pecel untuk konsumsi teman-teman OSIS. Bayu bertekad mengubah dirinya menjadi lebih populer dari Roy (Indra Widjaya), pacar Susan, yang dikenal piawai sebagai gitaris band sekolah mereka. Bayu kemudian membentuk band YOWIS BEN bersama Doni, Yayan, dan Nando. Dalam perjalanan mereka, berbagai konflik muncul dan menguji persahabatan serta impian mereka.',
                'description' => 'A comedy film directed by Fajar Nugros and Bayu Skak.',
            ],
            [
                'id' => 2,
                'title' => 'Sekawan Limo',
                'release_year' => 2024,
                'genre' => 'Comedy, Horror',
                'poster' => 'sekawan_limo.jpg',
                'synopsis' => 'Kisah horor komedi pendakian gunung.',
                'description' => 'A comedy horror film directed by Bayu Skak.',
            ],
        ];

        foreach ($movies as $movieData) {
            Movie::updateOrCreate(['id' => $movieData['id']], $movieData);
        }
    }
}
