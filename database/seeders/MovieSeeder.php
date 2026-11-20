<?php

namespace Database\Seeders;

use App\Models\Movie;
use Illuminate\Database\Seeder;

class MovieSeeder extends Seeder
{
    /**
     * Menyimpan daftar filmografi terkenal untuk seluruh 12 aktor IndoLens ke tabel movies MySQL.
     */
    public function run(): void
    {
        $movies = [
            // 1. Bayu Eko Moektito
            [
                'id' => 1,
                'title' => 'Yowis Ben',
                'release_year' => 2018,
                'genre' => 'Comedy, Music, Romance',
                'poster' => 'Yowis_Ben.jpg',
                'synopsis' => 'Bayu membentuk band berbahasa Jawa bernama Yowis Ben bersama sahabat-sahabatnya demi menarik perhatian Susan dan membuktikan kemampuan mereka.',
                'description' => 'Film komedi musikal arahan Fajar Nugros dan Bayu Skak.',
            ],
            [
                'id' => 2,
                'title' => 'Sekawan Limo',
                'release_year' => 2024,
                'genre' => 'Comedy, Horror',
                'poster' => null,
                'synopsis' => 'Kisah horor komedi lima pendaki gunung yang melanggar pantangan lokal di Gunung Madyopuro.',
                'description' => 'Film horor komedi arahan Bayu Skak.',
            ],
            // 2. Alice Norin
            [
                'id' => 3,
                'title' => 'Psikopat',
                'release_year' => 2005,
                'genre' => 'Horror, Thriller',
                'poster' => null,
                'synopsis' => 'Teror pembunuh misterius yang menghantui Mita dan rekan-rekannya dalam perjalanan menuju lokasi terpencil.',
                'description' => 'Film horor thriller Indonesia yang dibintangi Alice Norin.',
            ],
            [
                'id' => 4,
                'title' => 'Ketika Cinta Bertasbih',
                'release_year' => 2009,
                'genre' => 'Drama, Romance',
                'poster' => null,
                'synopsis' => 'Kisah perjuangan hidup dan cinta Khairul Azzam selama menempuh pendidikan di Mesir hingga pertemuannya dengan Eliana.',
                'description' => 'Film drama religi populer adaptasi novel Habiburrahman El Shirazy.',
            ],
            [
                'id' => 5,
                'title' => 'Kutuk',
                'release_year' => 2019,
                'genre' => 'Horror',
                'poster' => null,
                'synopsis' => 'Serangkaian kejadian mistis menimpa perawat baru di sebuah panti jompo milik Elena.',
                'description' => 'Film horor Indonesia yang dibintangi Alice Norin dan Shandy Aulia.',
            ],
            // 3. Angga Aldi Yunanda
            [
                'id' => 6,
                'title' => 'Dua Garis Biru',
                'release_year' => 2019,
                'genre' => 'Drama, Romance',
                'poster' => null,
                'synopsis' => 'Bima dan Dara, sepasang pelajar SMA, harus menghadapi konsekuensi besar dalam hidup dan keluarga mereka setelah melampaui batas.',
                'description' => 'Film drama keluarga garapan Gina S. Noer.',
            ],
            [
                'id' => 7,
                'title' => 'Cinta Pertama, Kedua & Ketiga',
                'release_year' => 2021,
                'genre' => 'Drama, Family, Romance',
                'poster' => null,
                'synopsis' => 'Raja dan Asia sama-sama merawat orang tua tunggal mereka hingga hubungan kedua keluarga membawa dilema perasaan.',
                'description' => 'Film drama keluarga Indonesia arahan Gina S. Noer.',
            ],
            [
                'id' => 8,
                'title' => 'My Annoying Brother',
                'release_year' => 2024,
                'genre' => 'Comedy, Drama',
                'poster' => null,
                'synopsis' => 'Atlet judo nasional Kemal harus kembali tinggal bersama kakaknya yang mantan narapidana setelah mengalami cedera berat.',
                'description' => 'Adaptasi Indonesia dari film drama komedi Korea Selatan.',
            ],
            // 4. Ario Bayu
            [
                'id' => 9,
                'title' => 'Laskar Pelangi',
                'release_year' => 2008,
                'genre' => 'Drama, Family',
                'poster' => null,
                'synopsis' => 'Kisah perjuangan sepuluh anak Belitung menempuh pendidikan dengan penuh semangat dan persahabatan.',
                'description' => 'Film drama legendaris adaptasi novel Andrea Hirata.',
            ],
            [
                'id' => 10,
                'title' => 'Soekarno: Indonesia Merdeka',
                'release_year' => 2013,
                'genre' => 'Biography, Drama, History',
                'poster' => null,
                'synopsis' => 'Biografi perjuangan Ir. Soekarno sejak masa muda hingga memproklamasikan kemerdekaan Republik Indonesia.',
                'description' => 'Film biografi sejarah arahan Hanung Bramantyo.',
            ],
            [
                'id' => 11,
                'title' => 'Gundala',
                'release_year' => 2019,
                'genre' => 'Action, Sci-Fi',
                'poster' => null,
                'synopsis' => 'Sancaka bangkit membela rakyat dengan kekuatan petir menghadapi jaringan kejahatan terorganisir yang dipimpin Ghazul dan Pengkor.',
                'description' => 'Film pahlawan super Jagat Sinema Bumilangit garapan Joko Anwar.',
            ],
            // 5. Babe Cabita
            [
                'id' => 12,
                'title' => 'Comic 8',
                'release_year' => 2014,
                'genre' => 'Action, Comedy',
                'poster' => null,
                'synopsis' => 'Delapan anak muda dengan latar belakang dan motif berbeda tanpa sengaja merampok bank yang sama secara bersamaan.',
                'description' => 'Film aksi komedi populer garapan Anggy Umbara.',
            ],
            [
                'id' => 13,
                'title' => 'Aku, Kau & KUA',
                'release_year' => 2014,
                'genre' => 'Comedy, Romance',
                'poster' => null,
                'synopsis' => 'Enam sahabat menghadapi berbagai dinamika percintaan dan kesiapan menuju jenjang pernikahan.',
                'description' => 'Film komedi romantis garapan Monty Tiwa.',
            ],
            [
                'id' => 14,
                'title' => 'The Underdogs',
                'release_year' => 2017,
                'genre' => 'Comedy, Drama',
                'poster' => null,
                'synopsis' => 'Empat sahabat yang kerap diremehkan di sekolah bertekad menjadi kreator YouTube terkenal.',
                'description' => 'Film komedi remaja garapan Adink Liwutang.',
            ],
            // 6. Bunga Citra Lestari
            [
                'id' => 15,
                'title' => 'Habibie & Ainun',
                'release_year' => 2012,
                'genre' => 'Biography, Drama, Romance',
                'poster' => null,
                'synopsis' => 'Kisah cinta dan dedikasi B.J. Habibie bersama istrinya Hasri Ainun Besari dalam membangun mimpi serta bangsa.',
                'description' => 'Film biografi romantis adaptasi buku karya B.J. Habibie.',
            ],
            [
                'id' => 16,
                'title' => 'My Stupid Boss',
                'release_year' => 2016,
                'genre' => 'Comedy',
                'poster' => null,
                'synopsis' => 'Diana harus menghadapi tingkah eksentrik, pelit, dan penuh kekonyolan dari atasannya di sebuah perusahaan di Kuala Lumpur.',
                'description' => 'Film komedi box office arahan Upi Avianto.',
            ],
            [
                'id' => 17,
                'title' => '3 Srikandi',
                'release_year' => 2016,
                'genre' => 'Biography, Drama, Sport',
                'poster' => null,
                'synopsis' => 'Perjuangan tiga pemanah putri Indonesia meraih medali Olimpiade pertama bagi Tanah Air di Seoul 1988.',
                'description' => 'Film biografi olahraga garapan Iman Brotoseno.',
            ],
            // 7. Chelsea Islan
            [
                'id' => 18,
                'title' => 'Merry Riana: Mimpi Sejuta Dolar',
                'release_year' => 2014,
                'genre' => 'Biography, Drama',
                'poster' => null,
                'synopsis' => 'Perjuangan mahasiswi Indonesia Merry Riana bertahan hidup dan merintis kesuksesan dari nol di Singapura.',
                'description' => 'Film biografi inspiratif garapan Hestu Saputra.',
            ],
            [
                'id' => 19,
                'title' => 'Guru Bangsa: Tjokroaminoto',
                'release_year' => 2015,
                'genre' => 'Biography, Drama, History',
                'poster' => null,
                'synopsis' => 'Perjalanan tokoh pergerakan nasional H.O.S. Tjokroaminoto dalam memperjuangkan kesetaraan dan kemerdekaan melalui Sarekat Islam.',
                'description' => 'Film drama sejarah epik garapan Garin Nugroho.',
            ],
            [
                'id' => 20,
                'title' => 'Ayat-Ayat Cinta 2',
                'release_year' => 2017,
                'genre' => 'Drama, Romance',
                'poster' => null,
                'synopsis' => 'Kehidupan Fahri di Edinburgh yang dipenuhi ujian kemanusiaan dan pertemuannya dengan tetangga bernama Keira.',
                'description' => 'Sekuel film drama religi arahan Guntur Soeharjanto.',
            ],
            // 8. Darius Sinathrya
            [
                'id' => 21,
                'title' => 'Merah Putih',
                'release_year' => 2009,
                'genre' => 'Action, Drama, War',
                'poster' => null,
                'synopsis' => 'Sekelompok kadet dengan latar suku dan agama berbeda bersatu mempertahankan kemerdekaan Indonesia pada 1947.',
                'description' => 'Bagian pertama Trilogi Merdeka arahan Yadi Sugandi.',
            ],
            [
                'id' => 22,
                'title' => 'Dilema',
                'release_year' => 2012,
                'genre' => 'Crime, Drama, Thriller',
                'poster' => null,
                'synopsis' => 'Lima kisah saling berkaitan tentang konflik moral antara hukum, keluarga, dan dunia kriminal di Jakarta.',
                'description' => 'Film antologi kriminal drama pemenang Indonesian Movie Awards.',
            ],
            [
                'id' => 23,
                'title' => 'Surga yang Tak Dirindukan 3',
                'release_year' => 2021,
                'genre' => 'Drama, Family',
                'poster' => null,
                'synopsis' => 'Kelanjutan kisah keluarga Pras dan Meirose yang kembali diuji dengan hadirnya masa lalu.',
                'description' => 'Film drama keluarga garapan Pritagita Arianegara.',
            ],
            // 9. Deva Mahenra
            [
                'id' => 24,
                'title' => 'Sabtu Bersama Bapak',
                'release_year' => 2016,
                'genre' => 'Drama, Family',
                'poster' => null,
                'synopsis' => 'Dua bersaudara Satya dan Cakra tumbuh dewasa dengan bimbingan rekaman video pesan kehidupan yang ditinggalkan ayah mereka.',
                'description' => 'Film drama keluarga adaptasi novel Adhitya Mulya.',
            ],
            [
                'id' => 25,
                'title' => 'Ghost Writer',
                'release_year' => 2019,
                'genre' => 'Comedy, Horror',
                'poster' => null,
                'synopsis' => 'Seorang penulis novel bekerja sama dengan arwah Vino untuk menyelesaikan buku berdasarkan kisah nyata di buku harian berhantu.',
                'description' => 'Film horor komedi garapan Bene Dion Rajagukguk.',
            ],
            [
                'id' => 26,
                'title' => 'Ipar Adalah Maut',
                'release_year' => 2024,
                'genre' => 'Drama',
                'poster' => null,
                'synopsis' => 'Keharmonisan rumah tangga Nisa dan Aris retak setelah adik kandung Nisa tinggal bersama mereka.',
                'description' => 'Film drama box office arahan Hanung Bramantyo.',
            ],
            // 10. Dian Sastrowardoyo
            [
                'id' => 27,
                'title' => 'Ada Apa dengan Cinta?',
                'release_year' => 2002,
                'genre' => 'Drama, Romance',
                'poster' => null,
                'synopsis' => 'Kisah persahabatan dan romansa remaja antara siswi populer Cinta dan penyair sekolah Rangga.',
                'description' => 'Film drama romantis ikonik Indonesia garapan Rudi Soedjarwo.',
            ],
            [
                'id' => 28,
                'title' => 'Kartini',
                'release_year' => 2017,
                'genre' => 'Biography, Drama, History',
                'poster' => null,
                'synopsis' => 'Perjuangan Raden Adjeng Kartini memperjuangkan hak pendidikan dan kesetaraan perempuan di era kolonial.',
                'description' => 'Film biografi sejarah arahan Hanung Bramantyo.',
            ],
            [
                'id' => 29,
                'title' => 'Aruna dan Lidahnya',
                'release_year' => 2018,
                'genre' => 'Comedy, Drama',
                'poster' => null,
                'synopsis' => 'Perjalanan kuliner dan investigasi wabah flu burung Aruna bersama sahabat-sahabatnya melintasi berbagai kota di Indonesia.',
                'description' => 'Film drama kuliner garapan Edwin adaptasi novel Laksmi Pamuntjak.',
            ],
            // 11. Dinda Kanyadewi
            [
                'id' => 30,
                'title' => 'Kawin Kontrak',
                'release_year' => 2008,
                'genre' => 'Comedy, Drama',
                'poster' => null,
                'synopsis' => 'Kisah komedi perjalanan tiga sahabat pria yang terlibat situasi kocak dan pelajaran hidup di sebuah desa.',
                'description' => 'Film komedi Indonesia garapan Ody C. Harahap.',
            ],
            [
                'id' => 31,
                'title' => 'Milly & Mamet: Ini Bukan Cinta & Rangga',
                'release_year' => 2018,
                'genre' => 'Comedy, Drama, Romance',
                'poster' => null,
                'synopsis' => 'Milly dan Mamet memulai babak baru kehidupan rumah tangga dan impian membuka restoran di tengah tekanan pekerjaan.',
                'description' => 'Film spin-off komedi romantis arahan Ernest Prakasa.',
            ],
            [
                'id' => 32,
                'title' => 'Badarawuhi di Desa Penari',
                'release_year' => 2024,
                'genre' => 'Horror',
                'poster' => null,
                'synopsis' => 'Teror mistis yang dialami Mila saat mengembalikan gelang pusaka ke desa terpencil yang dikuasai sosok Badarawuhi.',
                'description' => 'Film horor prekuel KKN di Desa Penari garapan Kimo Stamboel.',
            ],
            // 12. Dodit Mulyanto
            [
                'id' => 33,
                'title' => 'Cek Toko Sebelah',
                'release_year' => 2016,
                'genre' => 'Comedy, Drama, Family',
                'poster' => null,
                'synopsis' => 'Konflik keluarga hangat antara ayah dan dua anak laki-lakinya dalam meneruskan toko kelontong keluarga.',
                'description' => 'Film drama komedi keluarga arahan Ernest Prakasa.',
            ],
            [
                'id' => 34,
                'title' => 'Susah Sinyal',
                'release_year' => 2017,
                'genre' => 'Comedy, Drama, Family',
                'poster' => null,
                'synopsis' => 'Pengacara sibuk Ellen berusaha memperbaiki hubungan dengan putrinya melalui liburan ke Sumba yang minim sinyal.',
                'description' => 'Film drama komedi garapan Ernest Prakasa.',
            ],
            [
                'id' => 35,
                'title' => 'Rumah Dinas Bapak',
                'release_year' => 2024,
                'genre' => 'Comedy, Horror',
                'poster' => null,
                'synopsis' => 'Keluarga seorang mantri perhutani mengalami teror gaib saat pindah ke rumah dinas di tengah hutan jati.',
                'description' => 'Film horor komedi yang diangkat dari kisah nyata masa kecil Dodit Mulyanto.',
            ],
        ];

        foreach ($movies as $movieData) {
            Movie::updateOrCreate(
                ['title' => $movieData['title'], 'release_year' => $movieData['release_year']],
                collect($movieData)->except(['id'])->all()
            );
        }
    }
}
