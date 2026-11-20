<?php

namespace Database\Seeders;

use App\Models\Actor;
use App\Models\ActorImage;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class ActorImageSeeder extends Seeder
{
    /**
     * Mendaftarkan seluruh foto wajah aktor pada folder storage/app/public/actor-images/{id}-{slug}/
     * ke tabel actor_images MySQL tanpa menduplikasi data yang sudah tersimpan.
     */
    public function run(): void
    {
        $disk = Storage::disk('public');

        foreach (Actor::orderBy('id')->get() as $actor) {
            $slug = Str::slug($actor->full_name);
            $dirName = "actor-images/{$actor->id}-{$slug}";
            if (!$disk->exists($dirName)) {
                continue;
            }

            $files = $disk->files($dirName);
            sort($files);

            foreach ($files as $relativePath) {
                $basename = basename($relativePath);
                if (str_starts_with(strtolower($basename), 'profile-')) {
                    continue;
                }

                $ext = strtolower(pathinfo($basename, PATHINFO_EXTENSION));
                if (!in_array($ext, ['jpg', 'jpeg', 'png', 'webp', 'avif'], true)) {
                    continue;
                }

                ActorImage::firstOrCreate([
                    'actor_id' => $actor->id,
                    'image' => $relativePath,
                ]);
            }
        }
    }
}
