<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreActorRequest;
use App\Http\Requests\UpdateActorRequest;
use App\Models\Actor;
use App\Models\ActorImage;
use Carbon\Carbon;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class CampController extends Controller
{
    /**
     * Display a listing of actors with search and pagination for administration.
     */
    public function index(Request $request)
    {
        $query = Actor::query();

        // Search strictly by actor full_name
        if ($request->filled('search')) {
            $searchTerm = trim($request->input('search'));
            $query->where('full_name', 'LIKE', '%' . $searchTerm . '%');
        }

        // Pagination options: 5, 10, 25, 50 (default 10)
        $perPage = (int) $request->input('per_page', 10);
        if (!in_array($perPage, [5, 10, 25, 50], true)) {
            $perPage = 10;
        }

        $actors = $query->orderBy('full_name', 'asc')
            ->paginate($perPage)
            ->withQueryString();

        return view('camp.index', compact('actors', 'perPage'));
    }

    /**
     * Show form to add a new actor.
     */
    public function create()
    {
        return view('camp.create');
    }

    /**
     * Store newly created actor in MySQL database.
     */
    public function store(StoreActorRequest $request)
    {
        DB::transaction(function () use ($request) {
            // Map UI gender to existing database representation
            $gender = match (strtolower(trim((string)$request->input('gender')))) {
                'male', 'laki-laki' => 'Laki-laki',
                'female', 'perempuan' => 'Perempuan',
                default => null,
            };

            // Derive age from birth_date if not explicitly provided
            $age = $request->filled('age')
                ? (int) $request->input('age')
                : ($request->filled('birth_date') ? Carbon::parse($request->input('birth_date'))->age : null);

            // Handle optional primary photo upload
            $photoFilename = null;
            if ($request->hasFile('photo')) {
                $file = $request->file('photo');
                $photoFilename = Str::slug($request->input('full_name')) . '_' . uniqid() . '.' . $file->getClientOriginalExtension();
                $file->storeAs('actors', $photoFilename, 'public');
            }

            Actor::create([
                'full_name' => trim($request->input('full_name')),
                'gender' => $gender,
                'birth_date' => $request->input('birth_date') ?: null,
                'birth_place' => $request->input('birth_place') ? trim($request->input('birth_place')) : null,
                'age' => $age,
                'photo' => $photoFilename,
                'biography' => $request->input('biography') ? trim($request->input('biography')) : null,
                'instagram' => $request->input('instagram') ? trim($request->input('instagram')) : null,
                'wikipedia' => $request->input('wikipedia') ? trim($request->input('wikipedia')) : null,
                'imdb' => $request->input('imdb') ? trim($request->input('imdb')) : null,
            ]);
        });

        return redirect()->route('camp.index')->with('success', 'Actor added successfully.');
    }

    /**
     * Show form to edit an existing actor.
     */
    public function edit(string $id)
    {
        $actor = Actor::findOrFail($id);
        return view('camp.edit', compact('actor'));
    }

    /**
     * Update actor in MySQL database.
     */
    public function update(UpdateActorRequest $request, string $id)
    {
        $actor = Actor::findOrFail($id);

        DB::transaction(function () use ($request, $actor) {
            // Map UI gender to database representation
            $gender = match (strtolower(trim((string)$request->input('gender')))) {
                'male', 'laki-laki' => 'Laki-laki',
                'female', 'perempuan' => 'Perempuan',
                default => null,
            };

            $age = $request->filled('age')
                ? (int) $request->input('age')
                : ($request->filled('birth_date') ? Carbon::parse($request->input('birth_date'))->age : null);

            $data = [
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

            // If a new photo is uploaded, replace existing photo
            if ($request->hasFile('photo')) {
                $file = $request->file('photo');
                $photoFilename = Str::slug($request->input('full_name')) . '_' . uniqid() . '.' . $file->getClientOriginalExtension();
                $file->storeAs('actors', $photoFilename, 'public');

                // Clean up old photo file if it exists
                if ($actor->photo && Storage::disk('public')->exists('actors/' . $actor->photo)) {
                    Storage::disk('public')->delete('actors/' . $actor->photo);
                }

                $data['photo'] = $photoFilename;
            }

            $actor->update($data);
        });

        return redirect()->route('camp.index')->with('success', 'Actor updated successfully.');
    }

    /**
     * Delete actor and all related stored face images without leaving orphan files.
     */
    public function destroy(string $id)
    {
        $actor = Actor::with('images')->findOrFail($id);

        DB::transaction(function () use ($actor) {
            // Collect face images to delete from disk
            $faceImages = $actor->images;
            $primaryPhoto = $actor->photo;

            // Delete actor record (cascades actor_images in DB)
            $actor->delete();

            // Unlink face image files from storage
            foreach ($faceImages as $img) {
                if ($img->image && Storage::disk('public')->exists('actors/faces/' . $img->image)) {
                    Storage::disk('public')->delete('actors/faces/' . $img->image);
                }
            }

            // Unlink primary photo from storage if present
            if ($primaryPhoto && Storage::disk('public')->exists('actors/' . $primaryPhoto)) {
                Storage::disk('public')->delete('actors/' . $primaryPhoto);
            }
        });

        return redirect()->route('camp.index')->with('success', 'Actor deleted successfully.');
    }

    /**
     * Show the Add Face image management page for an actor.
     */
    public function faces(string $id)
    {
        $actor = Actor::with('images')->findOrFail($id);
        return view('camp.faces', compact('actor'));
    }

    /**
     * Upload multiple face images for an actor.
     * No arbitrary count or file-size restriction; strictly validates jpg/jpeg/png.
     */
    public function storeFaces(Request $request, string $id)
    {
        $actor = Actor::findOrFail($id);

        $request->validate([
            'images' => ['required', 'array', 'min:1'],
            'images.*' => ['required', 'file', 'image', 'mimes:jpg,jpeg,png'],
        ], [
            'images.required' => 'Please select at least one face image to upload.',
            'images.*.image' => 'The uploaded file must be a valid image.',
            'images.*.mimes' => 'Only .jpg, .jpeg, and .png images are allowed.',
        ]);

        DB::transaction(function () use ($request, $actor) {
            $files = $request->file('images', []);
            foreach ($files as $file) {
                $filename = Str::slug($actor->full_name) . '_face_' . uniqid() . '.' . $file->getClientOriginalExtension();
                $file->storeAs('actors/faces', $filename, 'public');

                ActorImage::create([
                    'actor_id' => $actor->id,
                    'image' => $filename,
                ]);
            }
        });

        return redirect()->route('camp.faces', $actor->id)->with('success', 'Face images uploaded successfully.');
    }

    /**
     * Delete an individual face image and remove the physical file.
     */
    public function destroyFace(string $actorId, string $imageId)
    {
        $actor = Actor::findOrFail($actorId);
        $imageRecord = ActorImage::where('actor_id', $actor->id)->where('id', $imageId)->firstOrFail();

        DB::transaction(function () use ($imageRecord) {
            $filename = $imageRecord->image;
            $imageRecord->delete();

            if ($filename && Storage::disk('public')->exists('actors/faces/' . $filename)) {
                Storage::disk('public')->delete('actors/faces/' . $filename);
            }
        });

        return redirect()->route('camp.faces', $actor->id)->with('success', 'Face image deleted successfully.');
    }

    /**
     * Session 6 Recognition Integration: Look up actor record in database by recognized name.
     * Enriches Session 5 recognition output with database record details.
     * Does NOT introduce aliases or biography search.
     */
    public function lookup(Request $request)
    {
        $rawName = trim((string) $request->input('name', ''));

        if ($rawName === '' || strcasecmp($rawName, 'Tidak Dikenali') === 0 || strcasecmp($rawName, 'unknown') === 0) {
            return response()->json([
                'found' => false,
                'actor' => null,
            ]);
        }

        // Search strictly against actors.full_name
        $actor = Actor::whereRaw('LOWER(TRIM(full_name)) = ?', [strtolower($rawName)])->first();

        if (!$actor) {
            return response()->json([
                'found' => false,
                'actor' => null,
            ]);
        }

        return response()->json([
            'found' => true,
            'actor' => [
                'id' => $actor->id,
                'full_name' => $actor->full_name,
                'gender' => $actor->gender_label,
                'age' => $actor->age,
                'birth_date' => $actor->birth_date ? Carbon::parse($actor->birth_date)->format('F d, Y') : null,
                'birth_place' => $actor->birth_place,
                'photo' => $actor->photo,
                'photo_url' => $actor->photo ? asset('storage/actors/' . $actor->photo) : null,
            ],
        ]);
    }
}
