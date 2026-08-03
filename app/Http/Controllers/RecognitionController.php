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
    public function upload(Request $request)
    {
        return $this->recognize($request);
    }

    /**
     * Validate video input and execute recognition pipeline.
     */
    public function recognize(Request $request)
    {
        $allowedExtensions = implode(',', config('recognition.allowed_extensions', ['mp4', 'avi', 'mov', 'mkv']));
        $maxSize = config('recognition.max_video_size', 51200);

        $request->validate([
            'video' => ['required', 'file', 'mimes:' . $allowedExtensions, 'max:' . $maxSize],
        ]);

        $videoPath = null;

        try {
            $videoPath = $this->recognitionService->storeTemporaryVideo($request->file('video'));
            $result = $this->recognitionService->recognizeVideo($videoPath);

            // Extract recognized actor names (ignoring 'unknown')
            $recognizedNames = [];
            $frames = $result['data']['frames'] ?? [];
            foreach ($frames as $frame) {
                foreach ($frame['detections'] ?? [] as $det) {
                    $name = $det['name'] ?? 'unknown';
                    if ($name !== 'unknown') {
                        // Normalize snake_case to Title Case (bayu_skak -> Bayu Skak)
                        $normalized = ucwords(str_replace('_', ' ', $name));
                        $recognizedNames[] = $normalized;
                    }
                }
            }
            session(['recognized_actor_names' => array_unique($recognizedNames)]);

            if ($request->wantsJson() || $request->ajax()) {
                return response()->json($result);
            }

            return view('pages.result', ['result' => $result]);
        } catch (Throwable $e) {
            \Illuminate\Support\Facades\Log::error('Recognition error: ' . $e->getMessage());
            if ($request->wantsJson() || $request->ajax()) {
                return response()->json([
                    'status' => 'error',
                    'message' => 'Recognition process failed.',
                ], 500);
            }

            return response()->json([
                'status' => 'error',
                'message' => 'Recognition process failed.',
            ], 500);
        } finally {
            if ($videoPath) {
                $this->recognitionService->cleanup($videoPath);
            }
        }
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
