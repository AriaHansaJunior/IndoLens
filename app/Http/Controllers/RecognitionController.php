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
            $videoUrl = url('/stream/video/' . $filename);

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
    /**
     * Execute recognition pipeline asynchronously on previously uploaded video.
     * Returns 202 Accepted immediately and starts Python process in background.
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
            $resultsDir = config('recognition.result_path', storage_path('app/ai/results'));
            if (!file_exists($resultsDir)) {
                mkdir($resultsDir, 0755, true);
            }

            $statusFilePath = $resultsDir . '/' . pathinfo(basename($videoToken), PATHINFO_FILENAME) . '.json';

            // Write initial processing status JSON
            file_put_contents($statusFilePath, json_encode([
                'status' => 'processing',
                'progress' => 0,
                'stage' => 'Initializing Recognition...',
                'video_url' => null,
                'actors' => []
            ], JSON_PRETTY_PRINT));

            // Metadata to pass to Python
            $actorMetadata = [
                'status_file_path' => $statusFilePath
            ];

            // Trigger background recognition
            $this->recognitionService->startBackgroundRecognition($videoPath, $actorMetadata);

            return response()->json([
                'status' => 'processing',
                'message' => 'Recognition started in background.',
                'video_token' => $videoToken,
                'status_file' => basename($statusFilePath)
            ], 202);
        } catch (Throwable $e) {
            \Illuminate\Support\Facades\Log::error('Recognition trigger error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Failed to trigger recognition: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get real-time status of async recognition process.
     */
    public function status($token)
    {
        $resultsDir = config('recognition.result_path', storage_path('app/ai/results'));
        $statusFilePath = $resultsDir . '/' . pathinfo(basename($token), PATHINFO_FILENAME) . '.json';

        if (!file_exists($statusFilePath)) {
            return response()->json([
                'status' => 'processing',
                'progress' => 0,
                'stage' => 'Initializing...',
                'video_url' => null,
                'actors' => []
            ]);
        }

        $content = file_get_contents($statusFilePath);
        $statusData = json_decode($content, true);

        if (!$statusData) {
            return response()->json([
                'status' => 'processing',
                'progress' => 0,
                'stage' => 'Reading status...',
                'video_url' => null,
                'actors' => []
            ]);
        }

        // If Python finished and wrote python_result
        if (isset($statusData['python_result'])) {
            $result = $statusData['python_result'];

            // Process enrichment if not already enriched
            if (!isset($statusData['enriched_data'])) {
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
                    $errorData = [
                        'status' => 'error',
                        'message' => 'Tidak ada muka manusia dalam video ini.'
                    ];
                    file_put_contents($statusFilePath, json_encode($errorData, JSON_PRETTY_PRINT));
                    return response()->json($errorData, 400);
                }

                $recognizedNames = array_values(array_unique($recognizedNames));

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

                if (empty($enrichedActors) && $hasUnknownFaces) {
                    $enrichedActors[] = [
                        'id' => 999,
                        'name' => 'Wajah tidak dikenali',
                        'character' => '',
                        'age' => '',
                        'filmography' => []
                    ];
                }

                $outputVideoPath = $result['data']['output_video'] ?? null;
                $videoUrl = null;
                if ($outputVideoPath && file_exists($outputVideoPath)) {
                    $filename = basename($outputVideoPath);
                    $publicResultsDir = public_path('results');
                    if (!file_exists($publicResultsDir)) {
                        mkdir($publicResultsDir, 0755, true);
                    }
                    copy($outputVideoPath, $publicResultsDir . '/' . $filename);
                    $videoUrl = url('/stream/video/' . $filename);
                }

                $finalData = [
                    'status' => 'completed',
                    'progress' => 100,
                    'stage' => 'Completed',
                    'video_url' => $videoUrl,
                    'actors' => $enrichedActors,
                    'data' => $result['data'] ?? []
                ];

                session([
                    'current_video_token' => $token,
                    'current_video_url' => $videoUrl,
                    'recognized_actor_names' => $recognizedNames,
                    'recognition_data' => $finalData
                ]);

                // Save enriched data back to JSON so subsequent polling hits instant response
                $statusData['enriched_data'] = $finalData;
                $statusData['status'] = 'completed';
                file_put_contents($statusFilePath, json_encode($statusData, JSON_PRETTY_PRINT));

                return response()->json($finalData);
            } else {
                return response()->json($statusData['enriched_data']);
            }
        }

        return response()->json($statusData);
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
