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
     * Handle video upload and initiate recognition workflow.
     */
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

            $videoPath = $this->recognitionService->storeTemporaryVideo($request->file('video'));
            $filename = basename($videoPath);

            // Copy to public uploads folder for instant web serving
            $publicUploadsDir = public_path('uploads');
            if (!file_exists($publicUploadsDir)) {
                mkdir($publicUploadsDir, 0755, true);
            }
            copy($videoPath, $publicUploadsDir . '/' . $filename);
            $videoUrl = asset('uploads/' . $filename);

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
     * Execute recognition pipeline on previously uploaded video.
     */
    /**
     * Execute recognition pipeline asynchronously on previously uploaded video.
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

        // Backwards compatibility if video file is sent directly to recognize endpoint
        if (!$videoPath && $request->hasFile('video')) {
            $allowedExtensions = implode(',', config('recognition.allowed_extensions', ['mp4', 'avi', 'mov', 'mkv']));
            $maxSize = config('recognition.max_video_size', 51200);

            $request->validate([
                'video' => ['required', 'file', 'mimes:' . $allowedExtensions, 'max:' . $maxSize],
            ]);

            $videoPath = $this->recognitionService->storeTemporaryVideo($request->file('video'));
            $videoToken = basename($videoPath);
        }

        if (!$videoPath || !file_exists($videoPath)) {
            return response()->json([
                'status' => 'error',
                'message' => 'Video file not found for recognition.',
            ], 400);
        }

        try {
            $resultsDir = storage_path('app/ai/results');
            if (!file_exists($resultsDir)) {
                mkdir($resultsDir, 0755, true);
            }

            $statusFilePath = $resultsDir . '/' . basename($videoToken) . '.json';
            
            // Initialize status JSON
            file_put_contents($statusFilePath, json_encode([
                'status' => 'processing',
                'progress' => 0,
                'stage' => 'Initializing...',
                'video_url' => null,
                'actors' => []
            ], JSON_PRETTY_PRINT));

            // Start background Python execution
            $this->recognitionService->startBackgroundRecognition($videoPath, [
                'video_token' => $videoToken,
                'status_file_path' => $statusFilePath
            ]);

            return response()->json([
                'status' => 'processing',
                'message' => 'Recognition process accepted and running in background.',
                'video_token' => $videoToken,
            ], 202);
        } catch (Throwable $e) {
            \Illuminate\Support\Facades\Log::error('Recognition start error: ' . $e->getMessage());
            return response()->json([
                'status' => 'error',
                'message' => 'Failed to initiate recognition process: ' . $e->getMessage(),
            ], 500);
        }
    }

    /**
     * Get recognition status and finalize when completed.
     */
    public function status(string $token)
    {
        $statusFilePath = storage_path('app/ai/results/' . basename($token) . '.json');

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
        $data = json_decode($content, true) ?: [];

        // If Python finished, perform Laravel finalization (video publish & actor session)
        if (($data['status'] ?? '') === 'finalizing') {
            $recognizedNames = [];
            $frames = $data['python_result']['data']['frames'] ?? [];
            foreach ($frames as $frame) {
                foreach ($frame['detections'] ?? [] as $det) {
                    $status = $det['status'] ?? 'unknown';
                    $actor = $det['actor'] ?? 'unknown';
                    if ($status === 'known' && $actor !== 'unknown' && $actor !== 'Tidak Dikenali') {
                        $normalized = ucwords(str_replace('_', ' ', $actor));
                        $recognizedNames[] = $normalized;

                        if (strtolower($actor) === 'bayu_eko_moektito' || strtolower($normalized) === 'bayu eko moektito') {
                            $recognizedNames[] = 'Bayu Skak';
                        }
                    }
                }
            }
            $recognizedNames = array_values(array_unique($recognizedNames));

            $outputVideoPath = $data['python_result']['data']['output_video'] ?? ($data['python_result']['output_video'] ?? null);
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
                'actors' => $recognizedNames,
                'data' => $data['python_result']['data'] ?? []
            ];

            session([
                'current_video_token' => $token,
                'current_video_url' => $videoUrl,
                'recognized_actor_names' => $recognizedNames,
                'recognition_data' => $finalData
            ]);

            file_put_contents($statusFilePath, json_encode($finalData, JSON_PRETTY_PRINT));
            return response()->json($finalData);
        }

        return response()->json($data);
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
