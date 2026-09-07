<?php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ExampleTest extends TestCase
{
    use RefreshDatabase;
    /**
     * A basic test example.
     */
    public function test_the_application_returns_a_successful_response(): void
    {
        $this->withoutVite();
        
        $response = $this->get('/');

        $response->assertStatus(200);
    }

    /**
     * Test the camera capture page loads successfully.
     */
    public function test_camera_capture_page_returns_successful_response(): void
    {
        $this->withoutVite();

        $response = $this->get('/camera');

        $response->assertStatus(200);
        $response->assertSee('Live Camera Capture');
        $response->assertSee('Camera Standby');
        $response->assertSee('Start Camera');
    }
}
