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
    protected $description = 'Migrate existing actor images to new actor-images/{id}-{slug} directory structure';

    /**
     * Execute the console command.
     */
    public function handle()
    {
        $actors = Actor::with('images')->get();
        $this->info("Starting migration of {$actors->count()} actors...");

        $disk = Storage::disk('public');

        foreach ($actors as $actor) {
            $slug = Str::slug($actor->full_name);
            $dirName = "actor-images/{$actor->id}-{$slug}";
            
            // Create directory if it doesn't exist
            if (!$disk->exists($dirName)) {
                $disk->makeDirectory($dirName);
            }

            DB::transaction(function () use ($actor, $dirName, $disk) {
                // 1. Migrate primary photo
                $oldPhoto = $actor->photo;
                
                // Only migrate if not already starting with actor-images/
                if ($oldPhoto && !str_starts_with($oldPhoto, 'actor-images/')) {
                    $oldPhotoPath = "actors/{$oldPhoto}";
                    
                    if ($disk->exists($oldPhotoPath)) {
                        // Extract extension from old photo
                        $ext = pathinfo($oldPhoto, PATHINFO_EXTENSION);
                        if (!$ext) $ext = 'jpg'; // Fallback
                        
                        $newPhotoName = "profile_{$actor->id}.{$ext}";
                        $newPhotoPath = "{$dirName}/{$newPhotoName}";
                        
                        // Copy file to new destination
                        $disk->copy($oldPhotoPath, $newPhotoPath);
                        
                        // Verify destination file exists
                        if ($disk->exists($newPhotoPath)) {
                            // Update DB
                            $actor->update(['photo' => $newPhotoPath]);
                            
                            // Delete old file
                            $disk->delete($oldPhotoPath);
                            $this->info("Migrated photo for {$actor->full_name}");
                        } else {
                            $this->error("Failed to copy photo for {$actor->full_name}");
                        }
                    }
                }

                // 2. Migrate face images
                foreach ($actor->images as $imgRecord) {
                    $oldImage = $imgRecord->image;
                    
                    // Only migrate if not already starting with actor-images/
                    if ($oldImage && !str_starts_with($oldImage, 'actor-images/')) {
                        $oldImagePath = "actors/faces/{$oldImage}";
                        
                        if ($disk->exists($oldImagePath)) {
                            $ext = pathinfo($oldImage, PATHINFO_EXTENSION);
                            if (!$ext) $ext = 'jpg';
                            
                            $newImageName = "face_{$imgRecord->id}_" . uniqid() . ".{$ext}";
                            $newImagePath = "{$dirName}/{$newImageName}";
                            
                            // Copy file
                            $disk->copy($oldImagePath, $newImagePath);
                            
                            // Verify copy
                            if ($disk->exists($newImagePath)) {
                                // Update DB
                                $imgRecord->update(['image' => $newImagePath]);
                                
                                // Delete old file
                                $disk->delete($oldImagePath);
                                $this->info("Migrated face image ID {$imgRecord->id} for {$actor->full_name}");
                            } else {
                                $this->error("Failed to copy face image ID {$imgRecord->id} for {$actor->full_name}");
                            }
                        }
                    }
                }
            });
        }

        $this->info('Migration completed successfully!');
    }
}
