<?php

namespace App\Services;

use Exception;

class ResultParserService
{
    /**
     * Parse Python JSON output string into structured data array.
     *
     * @throws Exception
     */
    public function parse(string $jsonContent): array
    {
        if (empty(trim($jsonContent))) {
            throw new Exception("Empty JSON response received from Python.");
        }

        $decoded = json_decode($jsonContent, true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new Exception("Failed to parse Python JSON output: " . json_last_error_msg());
        }

        $this->validateSchema($decoded);

        return $decoded;
    }

    /**
     * Validate schema structure of the JSON payload.
     */
    public function validateSchema(array $data): bool
    {
        return isset($data['status']);
    }

    /**
     * Alias for validateSchema.
     */
    public function validate(array $data): bool
    {
        return $this->validateSchema($data);
    }

    /**
     * Extract status from parsed data.
     */
    public function extractStatus(array $parsedData): string
    {
        return $parsedData['status'] ?? 'unknown';
    }

    /**
     * Extract frames array from parsed data.
     */
    public function extractFrames(array $parsedData): array
    {
        if (isset($parsedData['data']['frames'])) {
            return $parsedData['data']['frames'];
        }

        if (isset($parsedData['frames'])) {
            return $parsedData['frames'];
        }

        return [];
    }

    /**
     * Alias for extractFrames.
     */
    public function getFrames(array $parsedData): array
    {
        return $this->extractFrames($parsedData);
    }

    /**
     * Extract detections array from parsed data.
     */
    public function extractDetections(array $parsedData): array
    {
        if (isset($parsedData['data']['detections'])) {
            return $parsedData['data']['detections'];
        }

        if (isset($parsedData['detections'])) {
            return $parsedData['detections'];
        }

        return [];
    }

    /**
     * Alias for extractDetections.
     */
    public function getDetections(array $parsedData): array
    {
        return $this->extractDetections($parsedData);
    }
}
