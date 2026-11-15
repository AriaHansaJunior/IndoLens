<?php

namespace App\Console\Commands;

use App\Models\Actor;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class SyncActorEmbeddingsCommand extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'indolens:sync-embeddings {--force : Re-extract all embeddings even if already cached}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Synchronize all actor images from CAMP with Python YOLO FaceNet reference embeddings';

    /**
     * Execute the console command.
     */
    public function handle(): int
    {
        $yoloUrl = rtrim(config('recognition.yolo_service_url', 'http://127.0.0.1:8002'), '/');

        $this->info('IndoLens - Reference Embedding Synchronization');
        $this->line("Connecting to Python YOLO + FaceNet service on {$yoloUrl} ...");

        try {
            $healthRes = Http::timeout(3)->get("{$yoloUrl}/health");
            if (!$healthRes->ok()) {
                $this->error("YOLO service returned non-200 status from {$yoloUrl}.");
                return self::FAILURE;
            }
        } catch (\Throwable $e) {
            $this->error("Cannot reach YOLO service at {$yoloUrl}: " . $e->getMessage());
            return self::FAILURE;
        }

        $actors = Actor::with('images')->orderBy('id')->get();
        if ($actors->isEmpty()) {
            $this->warn('No actors found in database.');
            try {
                Http::timeout(5)->post("{$yoloUrl}/prune-orphaned-actors", [
                    'active_actors' => [],
                ]);
            } catch (\Throwable $e) {
                // Ignore service communication errors on empty database
            }
            return self::SUCCESS;
        }

        $this->info("Found {$actors->count()} actor(s) in database. Synchronizing reference face images...");

        // Prune orphaned actor references not present in MySQL
        $activeActorsPayload = $actors->map(function ($actor) {
            return [
                'actor_id' => $actor->id,
                'full_name' => $actor->full_name,
                'actor_slug' => Str::slug($actor->full_name, '_'),
            ];
        })->values()->toArray();

        $prunedOrphansCount = 0;
        try {
            $pruneRes = Http::timeout(10)->post("{$yoloUrl}/prune-orphaned-actors", [
                'active_actors' => $activeActorsPayload,
            ]);
            if ($pruneRes->ok()) {
                $pruneData = $pruneRes->json();
                $prunedOrphans = $pruneData['pruned_orphans'] ?? [];
                $prunedOrphansCount = count($prunedOrphans);
                if ($prunedOrphansCount > 0) {
                    $this->warn("  ✓ Pruned {$prunedOrphansCount} stale/orphaned actor folder(s): " . implode(', ', $prunedOrphans));
                }
            }
        } catch (\Throwable $e) {
            $this->warn('  ! Could not prune orphaned actors: ' . $e->getMessage());
        }

        $totalImagesSent = 0;
        $totalEmbeddingsGenerated = 0;
        $force = (bool) $this->option('force');

        foreach ($actors as $actor) {
            $this->line("Actor #{$actor->id}: <comment>{$actor->full_name}</comment>");
            $images = $actor->images;
            if ($images->isEmpty()) {
                $this->line('  - No face images uploaded in CAMP.');
                continue;
            }

            $disk = Storage::disk('public');
            $imagePayload = [];
            foreach ($images as $img) {
                if ($img->image && $disk->exists($img->image)) {
                    $imagePayload[] = [
                        'image_id' => $img->id,
                        'image_path' => $disk->path($img->image),
                    ];
                }
            }

            if (empty($imagePayload)) {
                $this->warn('  - Face images exist in DB but files not found on disk.');
                continue;
            }

            try {
                $response = Http::timeout(60)->post("{$yoloUrl}/sync-actor-embedding", [
                    'actor_id' => $actor->id,
                    'full_name' => $actor->full_name,
                    'images' => $imagePayload,
                    'force' => $force,
                ]);

                if ($response->ok()) {
                    $data = $response->json();
                    $genCount = $data['generated_count'] ?? 0;
                    $totalGen = $data['total_embeddings_for_actor'] ?? 0;
                    $prunedFiles = count($data['pruned_files'] ?? []);
                    $totalImagesSent += count($imagePayload);
                    $totalEmbeddingsGenerated += $genCount;

                    $msg = "  ✓ Synced {$genCount} embedding(s). Total active in reference: {$totalGen}";
                    if ($prunedFiles > 0) {
                        $msg .= " (Pruned {$prunedFiles} stale embedding files)";
                    }
                    $this->info($msg);
                } else {
                    $this->error("  ✗ Sync failed (HTTP {$response->status()}): " . $response->body());
                }
            } catch (\Throwable $e) {
                $this->error('  ✗ Error syncing embeddings: ' . $e->getMessage());
            }
        }

        // Final memory reload
        try {
            $reloadRes = Http::timeout(5)->post("{$yoloUrl}/reload-embeddings");
            if ($reloadRes->ok()) {
                $reloadStats = $reloadRes->json();
                $this->info('✓ In-memory reference embeddings fully updated across all actors.');
                $this->table(
                    ['Metric', 'Value'],
                    [
                        ['Total Actors in Database', $actors->count()],
                        ['Orphaned Actor Folders Pruned', $prunedOrphansCount],
                        ['Total Face Images Sent', $totalImagesSent],
                        ['Total Embeddings Generated', $totalEmbeddingsGenerated],
                        ['Active Actors in Microservice Memory', $reloadStats['actors_loaded'] ?? 'N/A'],
                    ]
                );
            }
        } catch (\Throwable $e) {
            $this->warn('Warning: Could not reload global embeddings: ' . $e->getMessage());
        }

        $this->info('Synchronization complete.');
        return self::SUCCESS;
    }
}
