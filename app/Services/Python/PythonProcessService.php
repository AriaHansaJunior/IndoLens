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
            $metaPath = storage_path('app/ai/temp/' . uniqid('meta_') . '.json');
            if (!file_exists(dirname($metaPath))) {
                mkdir(dirname($metaPath), 0755, true);
            }
            file_put_contents($metaPath, json_encode($actorMetadata));
            $args[] = $metaPath;
        }

        return $this->runCommand('recognize-video', $args);
    }

    /**
     * Run recognition command asynchronously in background.
     */
    public function runBackgroundRecognition(string $videoPath, array $actorMetadata = []): void
    {
        $args = [$videoPath];
        if (!empty($actorMetadata)) {
            $metaPath = storage_path('app/ai/temp/' . uniqid('meta_') . '.json');
            if (!file_exists(dirname($metaPath))) {
                mkdir(dirname($metaPath), 0755, true);
            }
            file_put_contents($metaPath, json_encode($actorMetadata));
            $args[] = $metaPath;
        }

        $cmd = $this->buildCommand('recognize-video', $args);

        $escapedCmd = array_map('escapeshellarg', $cmd);
        $escapedCmd[0] = escapeshellcmd($cmd[0]); // Don't use escapeshellarg on executable for Windows start command
        $cmdStr = implode(' ', $escapedCmd);

        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            // Include environment variables that might be missing in Laragon's shell
            $userProfile = getenv('USERPROFILE') ?: 'C:\Users\MATIUS AHJ';
            $logFile = storage_path('logs/python_bg.log');
            $bgCmd = 'set "USERPROFILE=' . $userProfile . '" && start /B "" ' . $cmdStr . ' > "' . $logFile . '" 2>&1';
            pclose(popen($bgCmd, 'r'));
        } else {
            $bgCmd = $cmdStr . ' > /dev/null 2>&1 &';
            exec($bgCmd);
        }
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

        $systemRoot = getenv('SystemRoot') ?: (getenv('SYSTEMROOT') ?: 'C:\\Windows');
        $path = getenv('PATH') ?: getenv('Path');

        $userProfile = getenv('USERPROFILE');
        $homeDrive = getenv('HOMEDRIVE');
        $homePath = getenv('HOMEPATH');

        $timeout = config('recognition.process_timeout', 0);

        $result = Process::env([
            'SystemRoot' => $systemRoot,
            'SYSTEMROOT' => $systemRoot,
            'PATH' => $path,
            'USERPROFILE' => $userProfile,
            'HOMEDRIVE' => $homeDrive,
            'HOMEPATH' => $homePath,
        ])->timeout($timeout)->run($command);
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
