<?php

namespace App\Services;

use App\Services\Python\PythonProcessService;
use App\Services\ResultParserService;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\File;
use Exception;

class RecognitionService
{
    protected PythonProcessService $pythonProcessService;
    protected ResultParserService $resultParserService;

    public function __construct(
        PythonProcessService $pythonProcessService,
        ResultParserService $resultParserService
    ) {
        $this->pythonProcessService = $pythonProcessService;
        $this->resultParserService = $resultParserService;
    }

    /**
     * Coordinate video recognition pipeline with optional actor metadata (LOCK 26).
     */
    public function recognizeVideo(string $videoPath, array $actorMetadata = []): array
    {
        $execution = $this->pythonProcessService->runRecognition($videoPath, $actorMetadata);
        $rawOutput = $execution['output'] ?? '';

        return $this->resultParserService->parse($rawOutput);
    }

    /**
     * Start video recognition asynchronously in background.
     */
    public function startBackgroundRecognition(string $videoPath, array $actorMetadata = []): void
    {
        $this->pythonProcessService->runBackgroundRecognition($videoPath, $actorMetadata);
    }

    /**
     * Store uploaded video temporarily for Python processing.
     */
    public function storeTemporaryVideo(UploadedFile $file): string
    {
        $tempDir = config('recognition.temporary_path', storage_path('app/ai/temp'));

        if (!File::exists($tempDir)) {
            File::makeDirectory($tempDir, 0755, true);
        }

        $filename = uniqid('video_', true) . '.' . $file->getClientOriginalExtension();
        $storedFile = $file->move($tempDir, $filename);

        return $storedFile->getRealPath();
    }

    /**
     * Remove temporary video file after processing.
     */
    public function cleanup(string $filePath): bool
    {
        if (File::exists($filePath)) {
            return File::delete($filePath);
        }
        return false;
    }

    /**
     * Coordinate actor recognition workflow (Reserved stub compatibility).
     */
    public function processRecognition(string $videoPath): array
    {
        return $this->recognizeVideo($videoPath);
    }
}
