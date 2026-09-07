<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Foundation\Vite;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        // Dual-access Vite support: allows seamless asset access from localhost, 127.0.0.1, and LAN IP (phone) over HTTP and HTTPS
        $this->app->singleton(Vite::class, function () {
            return new class extends Vite {
                protected function hotAsset($asset)
                {
                    $url = rtrim(file_get_contents($this->hotFile()));

                    if (function_exists('request') && request() && request()->getHost()) {
                        $clientHost = request()->getHost();
                        $parsed = parse_url($url);
                        $port = isset($parsed['port']) ? ':'.$parsed['port'] : ':5173';
                        
                        // Detect whether client or proxy is running over HTTPS
                        $isHttps = request()->isSecure() 
                            || request()->header('x-forwarded-proto') === 'https'
                            || (isset($parsed['scheme']) && $parsed['scheme'] === 'https');
                            
                        $scheme = $isHttps ? 'https' : 'http';
                        $url = "{$scheme}://{$clientHost}{$port}";
                    }

                    return $url.'/'.$asset;
                }
            };
        });
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        //
    }
}
