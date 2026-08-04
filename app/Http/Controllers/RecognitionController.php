<?php

namespace App\Http\Controllers;

use App\Services\RecognitionService;
use Illuminate\Http\Request;
use Throwable;

class RecognitionController extends Controller
{
    protected RecognitionService $recognitionService;

    public function __construct(RecognitionService $recognitionService)
    {
        $this->recognitionService = $recognitionService;
    }

    /**
     * Handle video upload and return instant original video response (< 1s).
     */
    public function upload(Request $request)
    {
        $allowedExtensions = implode(',', config('recognition.allowed_extensions', ['mp4', 'avi', 'mov', 'mkv']));
        $maxSize = config('recognition.max_video_size', 51200);

        $request->validate([
            'video' => ['required', 'file', 'mimes:' . $allowedExtensions, 'max:' . $maxSize],
        ]);

        try {
            // Reset recognized actors list for new video upload
            session()->forget('recognized_actor_names');
            session()->forget('current_video_url');
            session()->forget('recognition_data');

            $videoPath = $this->recognitionService->storeTemporaryVideo($request->file('video'));
            $filename = basename($videoPath);

            // Copy to public uploads folder for instant web serving
            $publicUploadsDir = public_path('uploads');
            if (!file_exists($publicUploadsDir)) {
                mkdir($publicUploadsDir, 0755, true);
            }
            copy($videoPath, $publicUploadsDir . '/' . $filename);
            $videoUrl = asset('uploads/' . $filename);

            // Save uploaded video URL in session for page navigation persistence
            session([
                'current_video_url' => $videoUrl,
                'current_video_token' => $filename,
            ]);

            return response()->json([
                'status' => 'success',
                'message' => 'Video uploaded successfully.',
                'video_token' => $filename,
                'video_path' => $videoPath,
                'video_url' => $videoUrl,
            ]);
        } catch (Throwable $e) {
            \Illuminate\Support\Facades\Log::error('Upload error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Video upload failed: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Clear the video session and return to initial state.
     */
    public function reset(Request $request)
    {
        $request->session()->forget([
            'current_video_token',
            'current_video_url',
            'recognized_actor_names',
            'recognition_data'
        ]);

        return response()->json(['status' => 'success']);
    }

    /**
     * Execute recognition pipeline synchronously on previously uploaded video.
     * Returns full result JSON when Python finishes.
     */
    public function recognize(Request $request)
    {
        $videoToken = $request->input('video_token');
        $videoPath = null;

        if ($videoToken) {
            $tempDir = config('recognition.temporary_path', storage_path('app/ai/temp'));
            $candidatePath = $tempDir . '/' . basename($videoToken);
            if (file_exists($candidatePath)) {
                $videoPath = $candidatePath;
            } else {
                $publicUploadPath = public_path('uploads/' . basename($videoToken));
                if (file_exists($publicUploadPath)) {
                    $videoPath = $publicUploadPath;
                }
            }
        }

        if (!$videoPath || !file_exists($videoPath)) {
            return response()->json([
                'status' => 'error',
                'message' => 'Video file not found for recognition.',
            ], 400);
        }

        try {
            // Prevent PHP from timing out during long recognition
            set_time_limit(0);
            ini_set('max_execution_time', 0);

            // Run Python recognition synchronously (waits until done)
            $result = $this->recognitionService->recognizeVideo($videoPath);

            // Check total faces detected across all frames
            $totalDetections = 0;
            $hasUnknownFaces = false;
            
            $recognizedNames = [];
            $frames = $result['data']['frames'] ?? [];
            foreach ($frames as $frame) {
                $dets = $frame['detections'] ?? [];
                $totalDetections += count($dets);
                
                foreach ($dets as $det) {
                    $status = $det['status'] ?? 'unknown';
                    $actor = $det['actor'] ?? 'unknown';
                    if ($status === 'known' && $actor !== 'unknown' && $actor !== 'Tidak Dikenali') {
                        $normalized = ucwords(str_replace('_', ' ', $actor));
                        $recognizedNames[] = $normalized;

                        if (strtolower($actor) === 'bayu_eko_moektito' || strtolower($normalized) === 'bayu eko moektito') {
                            $recognizedNames[] = 'Bayu Skak';
                        }
                    } else {
                        $hasUnknownFaces = true;
                    }
                }
            }

            if ($totalDetections === 0) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Tidak ada muka manusia dalam video ini.',
                ], 400);
            }

            $recognizedNames = array_values(array_unique($recognizedNames));

            // Enrich actors data for frontend pause overlay
            $enrichedActors = [];
            if (!empty($recognizedNames)) {
                $dbActors = \App\Models\Actor::whereIn('full_name', $recognizedNames)->with('characters.movie')->get();
                foreach ($dbActors as $dbActor) {
                    $characterName = $dbActor->characters->first() ? $dbActor->characters->first()->character_name : null;
                    
                    $filmography = [];
                    foreach ($dbActor->characters as $char) {
                        if ($char->movie) {
                            $filmography[] = $char->movie->title;
                        }
                    }
                    
                    $enrichedActors[] = [
                        'id' => $dbActor->id,
                        'name' => $dbActor->full_name,
                        'character' => $characterName,
                        'age' => $dbActor->age,
                        'filmography' => array_values(array_unique($filmography))
                    ];
                }
            }

            // Fallback if no actors matched in DB but detection returned names
            if (empty($enrichedActors) && !empty($recognizedNames)) {
                foreach ($recognizedNames as $idx => $name) {
                    $enrichedActors[] = [
                        'id' => $idx + 1,
                        'name' => $name,
                        'character' => 'Unknown',
                        'age' => 'Unknown',
                        'filmography' => []
                    ];
                }
            }

            // Fallback if no known faces at all but faces exist
            if (empty($enrichedActors) && $hasUnknownFaces) {
                $enrichedActors[] = [
                    'id' => 999,
                    'name' => 'Wajah tidak dikenali',
                    'character' => '',
                    'age' => '',
                    'filmography' => []
                ];
            }

            // Copy overlay video to public/results/
            $outputVideoPath = $result['data']['output_video'] ?? null;
            $videoUrl = null;
            if ($outputVideoPath && file_exists($outputVideoPath)) {
                $filename = basename($outputVideoPath);
                $publicResultsDir = public_path('results');
                if (!file_exists($publicResultsDir)) {
                    mkdir($publicResultsDir, 0755, true);
                }
                copy($outputVideoPath, $publicResultsDir . '/' . $filename);
                $videoUrl = asset('results/' . $filename);
            }

            $finalData = [
                'status' => 'completed',
                'progress' => 100,
                'stage' => 'Completed',
                'video_url' => $videoUrl,
                'actors' => $enrichedActors,
                'data' => $result['data'] ?? []
            ];

            // Persist session state so video survives page navigation
            session([
                'current_video_token' => $videoToken,
                'current_video_url' => $videoUrl,
                'recognized_actor_names' => $recognizedNames,
                'recognition_data' => $finalData
            ]);

            return response()->json($finalData);
        } catch (Throwable $e) {
            \Illuminate\Support\Facades\Log::error('Recognition error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Recognition failed: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Stream video with support for HTTP Range requests (fixes scrubbing/seeking)
     */
    public function streamVideo($filename)
    {
        $path = public_path('results/' . basename($filename));
        if (!file_exists($path)) {
            // Check uploads folder if it's the raw video
            $path = public_path('uploads/' . basename($filename));
            if (!file_exists($path)) {
                abort(404);
            }
        }
        
        return response()->file($path, [
            'Content-Type' => 'video/mp4',
            'Accept-Ranges' => 'bytes',
            'Cache-Control' => 'no-cache, private'
        ]);
    }

    /**
     * Display recognition results.
     */
    public function result(Request $request)
    {
        return response()->json([
            'status' => 'success',
            'message' => 'Result endpoint ready.',
            'data' => []
        ]);
    }
}
