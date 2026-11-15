<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreActorRequest;
use App\Http\Requests\UpdateActorRequest;
use App\Models\Actor;
use App\Models\ActorImage;
use App\Models\ActorRole;
use App\Models\Character;
use App\Models\Movie;
use Carbon\Carbon;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class CampController extends Controller
{
    public function index(Request $request)
    {
        $query = Actor::query();

        if ($request->filled('search')) {
            $searchTerm = trim($request->input('search'));
            $query->where('full_name', 'LIKE', '%' . $searchTerm . '%');
        }

        $perPage = (int) $request->input('per_page', 10);
        if (!in_array($perPage, [5, 10, 25, 50], true)) {
            $perPage = 10;
        }

        $actors = $query->orderBy('full_name', 'asc')
            ->paginate($perPage)
            ->withQueryString();

        return view('camp.index', compact('actors', 'perPage'));
    }

    public function create()
    {
        return view('camp.create');
    }

    public function store(StoreActorRequest $request)
    {
        DB::transaction(function () use ($request) {
            $attributes = $this->extractActorAttributes($request);
            $attributes['photo'] = null;

            $actor = Actor::create($attributes);

            if ($request->hasFile('photo')) {
                $file = $request->file('photo');
                $dirName = $this->actorDirectory($actor);
                $slug = Str::slug($actor->full_name);
                $ext = strtolower($file->getClientOriginalExtension() ?: 'jpg');
                $photoFilename = "profile-{$slug}.{$ext}";
                $file->storeAs($dirName, $photoFilename, 'public');

                $actor->update(['photo' => $dirName . '/' . $photoFilename]);
            }
        });

        return redirect()->route('camp.index')->with('success', 'Actor added successfully.');
    }

    public function edit(Actor $actor)
    {
        return view('camp.edit', compact('actor'));
    }

    public function update(UpdateActorRequest $request, Actor $actor)
    {
        $oldFullName = $actor->full_name;

        DB::transaction(function () use ($request, $actor) {
            $oldDirName = $this->actorDirectory($actor);
            $data = $this->extractActorAttributes($request);

            $newSlug = Str::slug($data['full_name']);
            $newDirName = "actor-images/{$actor->id}-{$newSlug}";

            if ($oldDirName !== $newDirName && Storage::disk('public')->exists($oldDirName)) {
                Storage::disk('public')->move($oldDirName, $newDirName);

                if ($actor->photo && str_starts_with($actor->photo, $oldDirName)) {
                    $data['photo'] = str_replace($oldDirName, $newDirName, $actor->photo);
                }

                $actor->images()->get()->each(function ($img) use ($oldDirName, $newDirName) {
                    if ($img->image && str_starts_with($img->image, $oldDirName)) {
                        $img->update(['image' => str_replace($oldDirName, $newDirName, $img->image)]);
                    }
                });
            }

            if ($request->hasFile('photo')) {
                $file = $request->file('photo');
                $ext = strtolower($file->getClientOriginalExtension() ?: 'jpg');
                $photoFilename = "profile-{$newSlug}-" . uniqid() . ".{$ext}";

                $currentPhoto = $data['photo'] ?? $actor->photo;
                if ($currentPhoto && Storage::disk('public')->exists($currentPhoto)) {
                    Storage::disk('public')->delete($currentPhoto);
                }

                $file->storeAs($newDirName, $photoFilename, 'public');
                $data['photo'] = $newDirName . '/' . $photoFilename;
            }

            $actor->update($data);
        });

        if ($oldFullName !== $actor->full_name) {
            $this->deleteActorFromYoloService($actor->id, $oldFullName);
            $imagePayload = $this->buildActorEmbeddingPayload($actor);
            if (!empty($imagePayload)) {
                $this->syncActorEmbeddingsWithYoloService($actor, $imagePayload);
            }
        }

        return redirect()->route('camp.index')->with('success', 'Actor updated successfully.');
    }

    public function destroy(Actor $actor)
    {
        $actor->loadMissing('images');
        $actorFullName = $actor->full_name;
        $actorId = $actor->id;

        DB::transaction(function () use ($actor) {
            $faceImages = $actor->images;
            $primaryPhoto = $actor->photo;
            $dirName = $this->actorDirectory($actor);

            $actor->delete();

            if (Storage::disk('public')->exists($dirName)) {
                Storage::disk('public')->deleteDirectory($dirName);
            }

            foreach ($faceImages as $img) {
                if ($img->image && Storage::disk('public')->exists($img->image)) {
                    Storage::disk('public')->delete($img->image);
                }
            }

            if ($primaryPhoto && Storage::disk('public')->exists($primaryPhoto)) {
                Storage::disk('public')->delete($primaryPhoto);
            }
        });

        $this->deleteActorFromYoloService($actorId, $actorFullName);

        return redirect()->route('camp.index')->with('success', 'Actor deleted successfully.');
    }

    public function faces(Actor $actor)
    {
        $actor->load('images');
        return view('camp.faces', compact('actor'));
    }

    public function storeFaces(Request $request, Actor $actor)
    {
        $request->validate([
            'images' => ['required', 'array', 'min:1'],
            'images.*' => ['required', 'file', 'mimes:jpg,jpeg,png,webp,avif', 'max:10240'],
        ], [
            'images.required' => 'Please select at least one face image to upload.',
            'images.*.mimes' => 'Only .jpg, .jpeg, .png, .webp, and .avif images are allowed.',
            'images.*.max' => 'Each face image must not exceed 10 MB.',
        ]);

        $uploadedCount = 0;
        DB::transaction(function () use ($request, $actor, &$uploadedCount) {
            $files = $request->file('images', []);
            $slug = Str::slug($actor->full_name);
            $dirName = $this->actorDirectory($actor);
            $disk = Storage::disk('public');

            if (!$disk->exists($dirName)) {
                $disk->makeDirectory($dirName);
            }

            $existingHashes = [];
            $existingNumbers = [];
            foreach ($actor->images as $img) {
                if ($img->image && $disk->exists($img->image)) {
                    $existingHashes[md5_file($disk->path($img->image))] = true;
                }
                if ($img->image && preg_match('/-(\d+)\.[a-z0-9]+$/i', $img->image, $matches)) {
                    $existingNumbers[(int) $matches[1]] = true;
                }
            }

            foreach ($disk->files($dirName) as $diskFile) {
                if (preg_match('/-(\d+)\.[a-z0-9]+$/i', $diskFile, $matches)) {
                    $existingNumbers[(int) $matches[1]] = true;
                }
            }

            $index = empty($existingNumbers) ? 1 : (max(array_keys($existingNumbers)) + 1);
            foreach ($files as $file) {
                $hash = md5_file($file->path());
                if (isset($existingHashes[$hash])) {
                    continue;
                }

                while (isset($existingNumbers[$index])) {
                    $index++;
                }

                $ext = strtolower($file->getClientOriginalExtension() ?: 'jpg');
                $filename = sprintf('%s-%02d.%s', $slug, $index, $ext);
                $existingNumbers[$index] = true;
                $index++;

                $file->storeAs($dirName, $filename, 'public');

                ActorImage::create([
                    'actor_id' => $actor->id,
                    'image' => $dirName . '/' . $filename,
                ]);

                $uploadedCount++;
                $existingHashes[$hash] = true;
            }
        });

        if ($uploadedCount > 0) {
            $this->syncActorEmbeddingsWithYoloService($actor, $this->buildActorEmbeddingPayload($actor));
        }

        return redirect()->route('camp.faces', $actor)->with('success', 'Face images uploaded successfully.');
    }

    public function destroyFace(Actor $actor, ActorImage $actorImage)
    {
        abort_if($actorImage->actor_id !== $actor->id, 404);

        $targetImageId = $actorImage->id;

        DB::transaction(function () use ($actor, $actorImage) {
            $filename = $actorImage->image;
            $actorImage->delete();

            if ($filename && Storage::disk('public')->exists($filename)) {
                Storage::disk('public')->delete($filename);
            } elseif ($filename && Storage::disk('public')->exists('actors/faces/' . $filename)) {
                Storage::disk('public')->delete('actors/faces/' . $filename);
            }

            $deletedNumber = -1;
            if (preg_match('/-(\d+)\.[a-zA-Z0-9]+$/', $filename, $matches)) {
                $deletedNumber = (int) $matches[1];
            }

            $remainingImages = ActorImage::where('actor_id', $actor->id)->get();
            $maxImage = null;
            $maxNumber = -1;

            foreach ($remainingImages as $img) {
                if (preg_match('/-(\d+)\.[a-zA-Z0-9]+$/', $img->image, $matches)) {
                    $num = (int) $matches[1];
                    if ($num > $maxNumber) {
                        $maxNumber = $num;
                        $maxImage = $img;
                    }
                }
            }

            if ($maxImage && $deletedNumber > 0 && $maxNumber > $deletedNumber) {
                $ext = pathinfo($maxImage->image, PATHINFO_EXTENSION);
                $slug = Str::slug($actor->full_name);
                $dirName = $this->actorDirectory($actor);
                $newPath = $dirName . '/' . sprintf('%s-%02d.%s', $slug, $deletedNumber, $ext);

                if (Storage::disk('public')->exists($maxImage->image)) {
                    Storage::disk('public')->move($maxImage->image, $newPath);
                    $maxImage->update(['image' => $newPath]);
                }
            }
        });

        $this->deleteActorEmbeddingFromYoloService($actor, $targetImageId);

        return redirect()->route('camp.faces', $actor)->with('success', 'Face image deleted successfully.');
    }

    public function destroyMultipleFaces(Request $request, Actor $actor)
    {
        $validated = $request->validate([
            'image_uuids' => ['required', 'array', 'min:1'],
            'image_uuids.*' => ['required', 'string'],
        ], [
            'image_uuids.required' => 'Please select at least one face image to delete.',
        ]);

        $targetImages = ActorImage::where('actor_id', $actor->id)
            ->whereIn('uuid', $validated['image_uuids'])
            ->get();

        abort_if($targetImages->isEmpty(), 404);

        $deletedCount = $targetImages->count();

        DB::transaction(function () use ($actor, $targetImages) {
            $disk = Storage::disk('public');

            foreach ($targetImages as $img) {
                $filename = $img->image;
                $img->delete();

                if ($filename && $disk->exists($filename)) {
                    $disk->delete($filename);
                } elseif ($filename && $disk->exists('actors/faces/' . $filename)) {
                    $disk->delete('actors/faces/' . $filename);
                }
            }

            $this->resequenceActorFaceFiles($actor);
        });

        $remainingPayload = $this->buildActorEmbeddingPayload($actor);
        if (empty($remainingPayload)) {
            $this->deleteActorFromYoloService($actor->id, $actor->full_name);
        } else {
            $this->syncActorEmbeddingsWithYoloService($actor, $remainingPayload);
        }

        $label = $deletedCount === 1 ? 'face image' : 'face images';
        return redirect()->route('camp.faces', $actor)->with('success', "{$deletedCount} {$label} deleted successfully.");
    }

    protected function resequenceActorFaceFiles(Actor $actor): void
    {
        $disk = Storage::disk('public');
        $slug = Str::slug($actor->full_name);
        $dirName = $this->actorDirectory($actor);
        $remaining = ActorImage::where('actor_id', $actor->id)->orderBy('id')->get();

        if ($remaining->isEmpty()) {
            return;
        }

        $staged = [];
        foreach ($remaining as $index => $img) {
            $ext = strtolower(pathinfo((string) $img->image, PATHINFO_EXTENSION) ?: 'jpg');
            $finalPath = sprintf('%s/%s-%02d.%s', $dirName, $slug, $index + 1, $ext);

            if ($img->image === $finalPath || !$img->image || !$disk->exists($img->image)) {
                continue;
            }

            $tmpPath = "{$dirName}/__tmp_reseq_{$img->id}.{$ext}";
            $disk->move($img->image, $tmpPath);
            $staged[] = [
                'record' => $img,
                'tmpPath' => $tmpPath,
                'finalPath' => $finalPath,
            ];
        }

        foreach ($staged as $item) {
            if ($disk->exists($item['finalPath'])) {
                $disk->delete($item['finalPath']);
            }
            $disk->move($item['tmpPath'], $item['finalPath']);
            $item['record']->update(['image' => $item['finalPath']]);
        }
    }

    public function roles(Actor $actor)
    {
        $actor->load(['characters.movie', 'roles']);
        $movies = Movie::orderBy('title', 'asc')->get();

        return view('camp.roles', compact('actor', 'movies'));
    }

    public function storeCharacter(Request $request, Actor $actor)
    {
        $request->validate([
            'movie_id' => ['nullable', 'integer', 'exists:movies,id'],
            'new_movie_title' => ['nullable', 'string', 'max:255', 'required_without:movie_id'],
            'new_movie_year' => ['nullable', 'integer', 'min:1900', 'max:2100'],
            'new_movie_genre' => ['nullable', 'string', 'max:255'],
            'character_name' => ['required', 'string', 'max:255'],
        ], [
            'new_movie_title.required_without' => 'Please select an existing movie or enter a new movie title.',
            'character_name.required' => 'Please enter the character name played in the movie.',
        ]);

        DB::transaction(function () use ($request, $actor) {
            $movieId = $request->input('movie_id');

            if (!$movieId && $request->filled('new_movie_title')) {
                $title = trim($request->input('new_movie_title'));
                $movie = Movie::whereRaw('LOWER(title) = ?', [strtolower($title)])->first();

                if (!$movie) {
                    $movie = Movie::create([
                        'title' => $title,
                        'release_year' => $request->filled('new_movie_year') ? (int) $request->input('new_movie_year') : null,
                        'genre' => $request->filled('new_movie_genre') ? trim($request->input('new_movie_genre')) : null,
                    ]);
                }

                $movieId = $movie->id;
            }

            Character::firstOrCreate([
                'actor_id' => $actor->id,
                'movie_id' => $movieId,
                'character_name' => trim($request->input('character_name')),
            ]);
        });

        return redirect()->route('camp.roles', $actor)->with('success', 'Filmography role added successfully.');
    }

    public function destroyCharacter(Actor $actor, Character $character)
    {
        abort_if($character->actor_id !== $actor->id, 404);
        $character->delete();

        return redirect()->route('camp.roles', $actor)->with('success', 'Filmography role deleted successfully.');
    }

    public function storeRole(Request $request, Actor $actor)
    {
        $request->validate([
            'movie_keywords' => ['required', 'string', 'max:255'],
            'character_name' => ['required', 'string', 'max:255'],
        ], [
            'movie_keywords.required' => 'Please provide movie or title keyword(s) for live recognition.',
            'character_name.required' => 'Please provide the character name to display when matched.',
        ]);

        ActorRole::updateOrCreate(
            [
                'actor_id' => $actor->id,
                'movie_keywords' => strtolower(trim($request->input('movie_keywords'))),
            ],
            [
                'character_name' => trim($request->input('character_name')),
            ]
        );

        return redirect()->route('camp.roles', $actor)->with('success', 'Recognition keyword role saved successfully.');
    }

    public function destroyRole(Actor $actor, ActorRole $actorRole)
    {
        abort_if($actorRole->actor_id !== $actor->id, 404);
        $actorRole->delete();

        return redirect()->route('camp.roles', $actor)->with('success', 'Recognition keyword role deleted successfully.');
    }

    public function lookup(Request $request)
    {
        $rawName = trim((string) $request->input('name', ''));

        if ($rawName === '' || strcasecmp($rawName, 'Tidak Dikenali') === 0 || strcasecmp($rawName, 'unknown') === 0) {
            return response()->json([
                'found' => false,
                'actor' => null,
            ]);
        }

        $actor = Actor::with('images')
            ->whereRaw('LOWER(TRIM(full_name)) = ?', [strtolower($rawName)])
            ->first();

        if (!$actor) {
            return response()->json([
                'found' => false,
                'actor' => null,
            ]);
        }

        return response()->json([
            'found' => true,
            'actor' => [
                'uuid' => $actor->uuid,
                'full_name' => $actor->full_name,
                'gender' => $actor->gender_label,
                'age' => $actor->age,
                'birth_date' => $actor->birth_date ? Carbon::parse($actor->birth_date)->format('F d, Y') : null,
                'birth_place' => $actor->birth_place,
                'photo' => $actor->photo,
                'photo_url' => $actor->photo_url,
                'current_character_name' => $actor->current_character_name,
            ],
        ]);
    }

    protected function extractActorAttributes(Request $request): array
    {
        $gender = match (strtolower(trim((string) $request->input('gender')))) {
            'male', 'laki-laki' => 'Laki-laki',
            'female', 'perempuan' => 'Perempuan',
            default => null,
        };

        $age = $request->filled('age')
            ? (int) $request->input('age')
            : ($request->filled('birth_date') ? Carbon::parse($request->input('birth_date'))->age : null);

        return [
            'full_name' => trim($request->input('full_name')),
            'gender' => $gender,
            'birth_date' => $request->input('birth_date') ?: null,
            'birth_place' => $request->input('birth_place') ? trim($request->input('birth_place')) : null,
            'age' => $age,
            'biography' => $request->input('biography') ? trim($request->input('biography')) : null,
            'instagram' => $request->input('instagram') ? trim($request->input('instagram')) : null,
            'wikipedia' => $request->input('wikipedia') ? trim($request->input('wikipedia')) : null,
            'imdb' => $request->input('imdb') ? trim($request->input('imdb')) : null,
        ];
    }

    protected function actorDirectory(Actor $actor): string
    {
        return 'actor-images/' . $actor->id . '-' . Str::slug($actor->full_name);
    }

    protected function buildActorEmbeddingPayload(Actor $actor): array
    {
        $disk = Storage::disk('public');
        $payload = [];
        foreach ($actor->images()->orderBy('id')->get() as $img) {
            if ($img->image && $disk->exists($img->image)) {
                $payload[] = [
                    'image_id' => $img->id,
                    'image_path' => $disk->path($img->image),
                ];
            }
        }
        return $payload;
    }

    protected function yoloServiceUrl(string $path): string
    {
        return rtrim(config('recognition.yolo_service_url', 'http://127.0.0.1:8002'), '/') . '/' . ltrim($path, '/');
    }

    protected function syncActorEmbeddingsWithYoloService(Actor $actor, array $imageItems): void
    {
        if (empty($imageItems)) {
            return;
        }

        try {
            Http::timeout(10)->post($this->yoloServiceUrl('sync-actor-embedding'), [
                'actor_id' => $actor->id,
                'full_name' => $actor->full_name,
                'images' => $imageItems,
            ]);
        } catch (\Throwable $e) {
            Log::warning('[CAMP] Could not sync actor embeddings with YOLO service: ' . $e->getMessage());
        }
    }

    protected function deleteActorEmbeddingFromYoloService(Actor $actor, int $imageId): void
    {
        try {
            Http::timeout(5)->delete($this->yoloServiceUrl('delete-actor-embedding'), [
                'actor_id' => $actor->id,
                'full_name' => $actor->full_name,
                'image_id' => $imageId,
            ]);
        } catch (\Throwable $e) {
            Log::warning('[CAMP] Could not delete actor embedding from YOLO service: ' . $e->getMessage());
        }
    }

    protected function deleteActorFromYoloService(int $actorId, string $fullName): void
    {
        try {
            Http::timeout(5)->delete($this->yoloServiceUrl('delete-actor'), [
                'actor_id' => $actorId,
                'full_name' => $fullName,
            ]);
        } catch (\Throwable $e) {
            Log::warning('[CAMP] Could not delete actor from YOLO service: ' . $e->getMessage());
        }
    }
}
