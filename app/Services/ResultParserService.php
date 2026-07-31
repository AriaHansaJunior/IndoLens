<?php

namespace App\Services;

class ResultParserService
{
    /**
     * Parse Python JSON output into structured data.
     */
    public function parse(string $jsonContent): array
    {
        // Reserved method to parse Python JSON output
        return json_decode($jsonContent, true) ?? [];
    }
}
