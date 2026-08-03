<?php

namespace App\Services\Python;

use Illuminate\Support\Facades\Process;
use Illuminate\Contracts\Process\ProcessResult;
use Exception;

class PythonProcessService
{
    protected ?ProcessResult $lastResult = null;

    /**
     * Run recognition command specifically for a video file, optionally passing actor metadata (LOCK 26).
     */
    public function runRecognition(string $videoPath, array $actorMetadata = []): array
    {
        $args = [$videoPath];
        if (!empty($actorMetadata)) {
            $args[] = json_encode($actorMetadata);
        }

        return $this->runCommand('recognize-video', $args);
    }

    /**
     * Run generic python command with arguments.
     */
    public function runCommand(string $command, array $arguments = []): array
    {
        $cmd = $this->buildCommand($command, $arguments);
        return $this->execute($cmd);
    }

    /**
     * Build the command array for Process execution.
     */
    public function buildCommand(string $command, array $arguments = []): array
    {
        $pythonBinary = config('recognition.python_binary', 'python');
        $pythonEntry = config('recognition.python_entry', base_path('python/main.py'));

        $cmd = [$pythonBinary, $pythonEntry, $command];

        foreach ($arguments as $arg) {
            $cmd[] = (string) $arg;
        }

        return $cmd;
    }

    /**
     * Execute Python process and return output details.
     *
     * @throws Exception
     */
    public function execute(array|string $command, array $arguments = []): array
    {
        if (is_string($command) && !empty($arguments)) {
            $command = $this->buildCommand($command, $arguments);
        }

        $result = Process::run($command);
        $this->lastResult = $result;

        $output = $this->captureOutput();
        $exitCode = $result->exitCode();

        if ($exitCode !== 0) {
            $errorMsg = $this->captureError();
            if (empty($errorMsg)) {
                $errorMsg = "Process exited with code {$exitCode}";
            }
            throw new Exception($errorMsg, $exitCode);
        }

        return [
            'exit_code' => $exitCode,
            'output' => $output,
        ];
    }

    /**
     * Capture standard output from the last executed process.
     */
    public function captureOutput(): string
    {
        return $this->lastResult ? $this->lastResult->output() : '';
    }

    /**
     * Capture standard error output from the last executed process.
     */
    public function captureError(): string
    {
        return $this->lastResult ? $this->lastResult->errorOutput() : '';
    }
}
