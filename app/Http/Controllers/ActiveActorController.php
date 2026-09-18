<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Actor;
use Illuminate\Support\Facades\DB;

class ActiveActorController extends Controller
{
    /**
     * Update the real-time detection status of actors based on Python payload.
     * POST /api/actors/active
     * Payload: { "actors": ["Bayu Eko Moektito"], "window_title": "Sekawan Limo - IDLIX - Google Chrome" }
     */
    public function updateActive(Request $request)
    {
        $rawActors   = $request->input('actors', []);
        $windowTitle = strtolower(trim((string)$request->input('window_title', '')));

        // Standardize input names to lowercase & trimmed for reliable comparison
        $cleanActors = array_filter(array_map(fn($name) => strtolower(trim((string)$name)), $rawActors));

        DB::transaction(function () use ($cleanActors, $windowTitle) {
            // Reset all actors to not detected, clear character context
            Actor::query()->update([
                'is_detected'            => false,
                'current_character_name' => null,
                'detected_window_title'  => null,
            ]);

            if (!empty($cleanActors)) {
                // Fetch all actors and find matches case-insensitively
                $allActors = Actor::with('roles')->get();

                foreach ($allActors as $actor) {
                    $actorFullName = strtolower(trim($actor->full_name));

                    // Check if this actor's name matches any detected name (case-insensitive)
                    if (in_array($actorFullName, $cleanActors, true)) {
                        $characterName = null;

                        // Try to find a matching role by checking if any movie keyword is contained in window title
                        foreach ($actor->roles as $role) {
                            $rawKeywords = explode(',', $role->movie_keywords);
                            foreach ($rawKeywords as $kw) {
                                $keyword = strtolower(trim($kw));
                                if ($keyword !== '' && $windowTitle !== '' && str_contains($windowTitle, $keyword)) {
                                    $characterName = $role->character_name;
                                    break 2; // Found best match
                                }
                            }
                        }

                        $actor->update([
                            'is_detected'            => true,
                            'current_character_name' => $characterName,
                            'detected_window_title'  => $windowTitle ?: null,
                        ]);
                    }
                }
            }
        });

        return response()->json(['status' => 'success', 'message' => 'Status updated.']);
    }

    /**
     * Fetch the list of currently detected actors for frontend polling.
     * GET /api/actors/active
     * Returns: { "detected_actors": ["Bayu Eko Moektito"], "character_map": {"Bayu Eko Moektito": "Bagas"} }
     */
    public function getActive()
    {
        $detectedActors = Actor::where('is_detected', true)
            ->get(['full_name', 'current_character_name']);

        $characterMap = $detectedActors->mapWithKeys(fn($a) => [
            $a->full_name => $a->current_character_name,
        ]);

        return response()->json([
            'detected_actors' => $detectedActors->pluck('full_name'),
            'character_map'   => $characterMap,
        ]);
    }
}
