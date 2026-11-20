<?php

namespace Database\Seeders;

use App\Models\Actor;
use Carbon\Carbon;
use Illuminate\Database\Seeder;

class ActorSeeder extends Seeder
{
    /**
     * Menyimpan seluruh 12 aktor terdaftar IndoLens beserta biodata dan tautan profil eksternal ke tabel actors MySQL.
     */
    public function run(): void
    {
        $actors = [
            [
                'id' => 1,
                'full_name' => 'Bayu Eko Moektito',
                'birth_date' => '1993-11-13',
                'birth_place' => 'Malang, Jawa Timur',
                'age' => Carbon::parse('1993-11-13')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/1-bayu-eko-moektito/profile-bayu-eko-moektito.jpg',
                'biography' => 'Bayu Eko Moektito, lebih dikenal sebagai Bayu Skak, adalah seorang aktor, sutradara, komedian, dan YouTuber Indonesia. Ia dikenal luas berkat perannya dalam seri film Yowis Ben dan Sekawan Limo.',
                'instagram' => 'https://www.instagram.com/moektito',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Bayu_Skak',
                'imdb' => 'https://www.imdb.com/name/nm8662914/',
            ],
            [
                'id' => 2,
                'full_name' => 'Alice Norin',
                'birth_date' => '1987-06-21',
                'birth_place' => 'Stavanger, Norwegia',
                'age' => Carbon::parse('1987-06-21')->age,
                'gender' => 'Perempuan',
                'photo' => 'actor-images/2-alice-norin/profile-alice-norin.jpg',
                'biography' => 'Alice Norin adalah aktris, model, dan pengusaha berkebangsaan Indonesia keturunan Norwegia-Sunda. Ia memulai karier di dunia modeling sebelum dikenal luas lewat berbagai film layar lebar dan sinetron seperti Ketika Cinta Bertasbih dan Kutuk.',
                'instagram' => 'https://www.instagram.com/alicenorin',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Alice_Norin',
                'imdb' => 'https://www.imdb.com/name/nm3472155/',
            ],
            [
                'id' => 3,
                'full_name' => 'Angga Aldi Yunanda',
                'birth_date' => '2000-05-16',
                'birth_place' => 'Lombok, Nusa Tenggara Barat',
                'age' => Carbon::parse('2000-05-16')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/3-angga-aldi-yunanda/profile-angga-aldi-yunanda.jpg',
                'biography' => 'Angga Aldi Yunanda adalah aktor dan penyanyi Indonesia yang melejit berkat perannya dalam film Dua Garis Biru. Ia telah membintangi berbagai film drama, romansa, dan komedi populer serta meraih sejumlah nominasi Piala Citra.',
                'instagram' => 'https://www.instagram.com/angga',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Angga_Yunanda',
                'imdb' => 'https://www.imdb.com/name/nm10174507/',
            ],
            [
                'id' => 4,
                'full_name' => 'Ario Bayu',
                'birth_date' => '1985-02-06',
                'birth_place' => 'Jakarta, Indonesia',
                'age' => Carbon::parse('1985-02-06')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/4-ario-bayu/profile-ario-bayu.jpg',
                'biography' => 'Ario Bayu adalah aktor senior Indonesia yang dikenal lewat kemampuan akting watak di film drama sejarah, laga, dan thriller. Ia memerankan tokoh proklamator dalam film Soekarno serta tampil di Laskar Pelangi, Rumah Dara, dan Gundala.',
                'instagram' => 'https://www.instagram.com/bayu_ario',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Ario_Bayu',
                'imdb' => 'https://www.imdb.com/name/nm2697841/',
            ],
            [
                'id' => 5,
                'full_name' => 'Babe Cabita',
                'birth_date' => '1989-06-05',
                'birth_place' => 'Medan, Sumatera Utara',
                'age' => 34,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/5-babe-cabita/profile-babe-cabita.jpg',
                'biography' => 'Priya Prayogha Pratama, lebih dikenal sebagai Babe Cabita (1989–2024), adalah pelawak tunggal dan aktor komedi Indonesia pemenang Stand Up Comedy Indonesia musim ke-3. Ia dikenal lewat perannya di seri film Comic 8, Aku, Kau & KUA, dan The Underdogs.',
                'instagram' => 'https://www.instagram.com/babecabita',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Babe_Cabita',
                'imdb' => 'https://www.imdb.com/name/nm6653200/',
            ],
            [
                'id' => 6,
                'full_name' => 'Bunga Citra Lestari',
                'birth_date' => '1983-03-22',
                'birth_place' => 'Jakarta, Indonesia',
                'age' => Carbon::parse('1983-03-22')->age,
                'gender' => 'Perempuan',
                'photo' => 'actor-images/6-bunga-citra-lestari/profile-bunga-citra-lestari.jpg',
                'biography' => 'Bunga Citra Lestari, akrab disapa BCL, adalah penyanyi dan aktris papan atas Indonesia. Di dunia perfilman, ia meraih kesuksesan besar lewat perannya sebagai Ainun dalam Habibie & Ainun, Diana dalam My Stupid Boss, dan Nurfitriyana dalam 3 Srikandi.',
                'instagram' => 'https://www.instagram.com/itsmebcl',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Bunga_Citra_Lestari',
                'imdb' => 'https://www.imdb.com/name/nm2716936/',
            ],
            [
                'id' => 7,
                'full_name' => 'Chelsea Islan',
                'birth_date' => '1995-06-02',
                'birth_place' => 'Queens, New York, Amerika Serikat',
                'age' => Carbon::parse('1995-06-02')->age,
                'gender' => 'Perempuan',
                'photo' => 'actor-images/7-chelsea-islan/profile-chelsea-islan.jpg',
                'biography' => 'Chelsea Elizabeth Islan adalah aktris Indonesia yang dikenal melalui berbagai peran utama di film biografi, drama sejarah, dan komedi. Ia mencuri perhatian publik lewat Merry Riana: Mimpi Sejuta Dolar, Guru Bangsa: Tjokroaminoto, dan Ayat-Ayat Cinta 2.',
                'instagram' => 'https://www.instagram.com/chelseaislan',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Chelsea_Islan',
                'imdb' => 'https://www.imdb.com/name/nm6041695/',
            ],
            [
                'id' => 8,
                'full_name' => 'Darius Sinathrya',
                'birth_date' => '1985-05-21',
                'birth_place' => 'Kloten, Swiss',
                'age' => Carbon::parse('1985-05-21')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/8-darius-sinathrya/profile-darius-sinathrya.jpg',
                'biography' => 'Darius Sinathrya adalah aktor, presenter, dan produser Indonesia. Ia dikenal luas sebagai pemeran Marius dalam trilogi film sejarah Merah Putih serta tampil dalam film Dilema dan Surga yang Tak Dirindukan 3.',
                'instagram' => 'https://www.instagram.com/darius_sinathrya',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Darius_Sinathrya',
                'imdb' => 'https://www.imdb.com/name/nm2760636/',
            ],
            [
                'id' => 9,
                'full_name' => 'Deva Mahenra',
                'birth_date' => '1990-04-19',
                'birth_place' => 'Makassar, Sulawesi Selatan',
                'age' => Carbon::parse('1990-04-19')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/9-deva-mahenra/profile-deva-mahenra.jpg',
                'biography' => 'Deva Mahenra adalah aktor, presenter, dan model Indonesia yang memulai karier di dunia hiburan sebelum menonjol di layar lebar. Ia dikenal melalui film Sabtu Bersama Bapak, Ghost Writer, serta fenomena box office Ipar Adalah Maut.',
                'instagram' => 'https://www.instagram.com/devamahenra',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Deva_Mahenra',
                'imdb' => 'https://www.imdb.com/name/nm6055225/',
            ],
            [
                'id' => 10,
                'full_name' => 'Dian Sastrowardoyo',
                'birth_date' => '1982-03-16',
                'birth_place' => 'Jakarta, Indonesia',
                'age' => Carbon::parse('1982-03-16')->age,
                'gender' => 'Perempuan',
                'photo' => 'actor-images/10-dian-sastrowardoyo/profile-dian-sastrowardoyo.jpg',
                'biography' => 'Diandra Paramita Sastrowardoyo adalah aktris dan produser terkemuka Indonesia peraih Piala Citra. Ia menjadi ikon perfilman nasional lewat peran Cinta dalam Ada Apa dengan Cinta?, serta tampil memukau dalam Kartini dan Aruna dan Lidahnya.',
                'instagram' => 'https://www.instagram.com/therealdisastr',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Dian_Sastrowardoyo',
                'imdb' => 'https://www.imdb.com/name/nm1099909/',
            ],
            [
                'id' => 11,
                'full_name' => 'Dinda Kanyadewi',
                'birth_date' => '1987-02-05',
                'birth_place' => 'Balikpapan, Kalimantan Timur',
                'age' => Carbon::parse('1987-02-05')->age,
                'gender' => 'Perempuan',
                'photo' => 'actor-images/11-dinda-kanyadewi/profile-dinda-kanyadewi.jpg',
                'biography' => 'Dinda Kanyadewi adalah aktris Indonesia yang dikenal lewat kemampuan akting beragam di sinetron maupun film layar lebar. Ia tampil dalam Kawin Kontrak, Milly & Mamet: Ini Bukan Cinta & Rangga, serta Badarawuhi di Desa Penari.',
                'instagram' => 'https://www.instagram.com/dindakanyaa',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Dinda_Kanyadewi',
                'imdb' => 'https://www.imdb.com/name/nm2934127/',
            ],
            [
                'id' => 12,
                'full_name' => 'Dodit Mulyanto',
                'birth_date' => '1985-06-30',
                'birth_place' => 'Blitar, Jawa Timur',
                'age' => Carbon::parse('1985-06-30')->age,
                'gender' => 'Laki-laki',
                'photo' => 'actor-images/12-dodit-mulyanto/profile-dodit-mulyanto.jpg',
                'biography' => 'Dodit Wahyudi Mulyanto adalah pelawak tunggal, aktor, musisi, dan penulis skenario Indonesia jebolan Stand Up Comedy Indonesia musim ke-4. Ia dikenal lewat gaya komedi khasnya dalam film Cek Toko Sebelah, Susah Sinyal, dan Rumah Dinas Bapak.',
                'instagram' => 'https://www.instagram.com/dodit_mul',
                'wikipedia' => 'https://id.wikipedia.org/wiki/Dodit_Mulyanto',
                'imdb' => 'https://www.imdb.com/name/nm7215266/',
            ],
        ];

        foreach ($actors as $actorData) {
            // Menjaga record aktor yang sudah ada (misal Bayu Eko Moektito) tanpa menimpa UUID lama
            $existing = Actor::where('full_name', $actorData['full_name'])
                ->orWhere('id', $actorData['id'])
                ->first();

            if ($existing) {
                $updateFields = collect($actorData)->except(['id'])->all();
                $existing->update($updateFields);
            } else {
                $newActor = new Actor(collect($actorData)->except(['id'])->all());
                $newActor->id = $actorData['id'];
                $newActor->save();
            }
        }
    }
}
