<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\Actor;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\DB;

class MigrateActorImages extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:migrate-actor-images';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Standardize actor photos and face images into actor-images/{id}-{slug}/{slug}-{number}.{ext}';

    public function handle(): int
    {
        $actors = Actor::with(['images' => fn ($q) => $q->orderBy('id')])->orderBy('id')->get();
        $this->info("Standardizing storage layout for {$actors->count()} actor(s)...");

        $disk = Storage::disk('public');

        foreach ($actors as $actor) {
            $slug = Str::slug($actor->full_name);
            $dirName = "actor-images/{$actor->id}-{$slug}";

            if (!$disk->exists($dirName)) {
                $disk->makeDirectory($dirName);
            }

            DB::transaction(function () use ($actor, $slug, $dirName, $disk) {
                $this->migrateProfilePhoto($actor, $slug, $dirName, $disk);
                $this->migrateFaceImages($actor, $slug, $dirName, $disk);
                $this->cleanupLegacyActorDirectories($actor, $dirName, $disk);
            });
        }

        $this->info('Standardization completed successfully!');

        return self::SUCCESS;
    }

    private function migrateProfilePhoto(Actor $actor, string $slug, string $dirName, $disk): void
    {
        $oldPhoto = $actor->photo;
        if (!$oldPhoto || str_starts_with($oldPhoto, 'http://') || str_starts_with($oldPhoto, 'https://')) {
            return;
        }

        $sourcePath = null;
        foreach ([$oldPhoto, "actors/{$oldPhoto}"] as $candidate) {
            if ($disk->exists($candidate)) {
                $sourcePath = $candidate;
                break;
            }
        }

        if (!$sourcePath) {
            return;
        }

        $ext = strtolower(pathinfo($sourcePath, PATHINFO_EXTENSION) ?: 'jpg');
        $targetPath = "{$dirName}/profile-{$slug}.{$ext}";

        if ($sourcePath === $targetPath) {
            return;
        }

        if ($disk->exists($targetPath)) {
            $disk->delete($targetPath);
        }

        $disk->move($sourcePath, $targetPath);
        $actor->update(['photo' => $targetPath]);
        $this->info("Moved profile photo for {$actor->full_name} -> {$targetPath}");
    }

    private function migrateFaceImages(Actor $actor, string $slug, string $dirName, $disk): void
    {
        $images = $actor->images->sortBy('id')->values();
        if ($images->isEmpty()) {
            return;
        }

        $alreadyStandardized = true;
        foreach ($images as $idx => $imgRecord) {
            $ext = strtolower(pathinfo((string) $imgRecord->image, PATHINFO_EXTENSION) ?: 'jpg');
            $expectedPath = sprintf('%s/%s-%02d.%s', $dirName, $slug, $idx + 1, $ext);
            if ($imgRecord->image !== $expectedPath || !$disk->exists($expectedPath)) {
                $alreadyStandardized = false;
                break;
            }
        }

        if ($alreadyStandardized) {
            return;
        }

        $staged = [];
        foreach ($images as $imgRecord) {
            $oldImage = (string) $imgRecord->image;
            $sourcePath = null;

            foreach ([$oldImage, "actors/faces/{$oldImage}"] as $candidate) {
                if ($candidate !== '' && $disk->exists($candidate)) {
                    $sourcePath = $candidate;
                    break;
                }
            }

            if (!$sourcePath) {
                $this->warn("Skipped missing file for face ID {$imgRecord->id}: {$oldImage}");
                continue;
            }

            $ext = strtolower(pathinfo($sourcePath, PATHINFO_EXTENSION) ?: 'jpg');
            $tmpPath = "{$dirName}/__tmp_face_{$imgRecord->id}.{$ext}";
            $disk->move($sourcePath, $tmpPath);

            $staged[] = [
                'record' => $imgRecord,
                'tmpPath' => $tmpPath,
                'ext' => $ext,
            ];
        }

        foreach ($staged as $idx => $item) {
            $finalPath = sprintf('%s/%s-%02d.%s', $dirName, $slug, $idx + 1, $item['ext']);
            if ($disk->exists($finalPath)) {
                $disk->delete($finalPath);
            }
            $disk->move($item['tmpPath'], $finalPath);
            $item['record']->update(['image' => $finalPath]);
            $this->info("Standardized face ID {$item['record']->id} -> {$finalPath}");
        }
    }

    private function cleanupLegacyActorDirectories(Actor $actor, string $canonicalDir, $disk): void
    {
        $prefix = "actor-images/{$actor->id}-";
        foreach ($disk->directories('actor-images') as $dir) {
            if ($dir !== $canonicalDir && str_starts_with($dir, $prefix)) {
                if (empty($disk->files($dir)) && empty($disk->directories($dir))) {
                    $disk->deleteDirectory($dir);
                    $this->info("Removed empty legacy directory: {$dir}");
                }
            }
        }
    }
}
