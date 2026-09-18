<?php

namespace Tests\Feature;

use App\Models\Actor;
use App\Models\ActorImage;
use App\Models\Character;
use App\Models\Movie;
use Carbon\Carbon;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

class CampTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->withoutVite();
        Storage::fake('public');
    }

    public function test_camp_index_page_loads_successfully(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
            'birth_date' => '1993-11-13',
            'age' => 31,
        ]);

        $response = $this->get('/camp');

        $response->assertStatus(200);
        $response->assertSee('CAMP');
        $response->assertSee('Bayu Eko Moektito');
        $response->assertSee('Add New Actor');
        $response->assertSee('Edit');
        $response->assertSee('Add Face');
        $response->assertSee('Delete');
        $response->assertSee('Rows per page:');
    }

    public function test_create_actor_successfully(): void
    {
        $response = $this->post('/camp', [
            'full_name' => 'Adipati Dolken',
            'gender' => 'Male',
            'birth_date' => '1991-08-19',
            'birth_place' => 'Jakarta',
            'age' => 33,
            'biography' => 'Indonesian actor and model.',
            'instagram' => 'https://www.instagram.com/adipati',
            'wikipedia' => 'https://id.wikipedia.org/wiki/Adipati_Dolken',
            'imdb' => 'https://www.imdb.com/name/nm3972235/',
        ]);

        $response->assertRedirect('/camp');
        $response->assertSessionHas('success', 'Actor added successfully.');

        $this->assertDatabaseHas('actors', [
            'full_name' => 'Adipati Dolken',
            'gender' => 'Laki-laki', // Verified mapping from Male
            'birth_place' => 'Jakarta',
            'age' => 33,
        ]);
    }

    public function test_create_actor_duplicate_name_rejected(): void
    {
        Actor::create([
            'full_name' => 'Iqbaal Ramadhan',
            'gender' => 'Laki-laki',
        ]);

        $response = $this->post('/camp', [
            'full_name' => 'Iqbaal Ramadhan',
            'gender' => 'Male',
        ]);

        $response->assertSessionHasErrors([
            'full_name' => 'Actor already exists.',
        ]);

        $this->assertEquals(1, Actor::where('full_name', 'Iqbaal Ramadhan')->count());
    }

    public function test_create_actor_name_with_numbers_rejected(): void
    {
        $response = $this->post('/camp', [
            'full_name' => 'Bayu123',
            'gender' => 'Male',
        ]);

        $response->assertSessionHasErrors('full_name');
        $this->assertDatabaseMissing('actors', ['full_name' => 'Bayu123']);
    }

    public function test_create_actor_future_birth_date_rejected(): void
    {
        $futureDate = Carbon::tomorrow()->format('Y-m-d');

        $response = $this->post('/camp', [
            'full_name' => 'Reza Rahadian',
            'birth_date' => $futureDate,
        ]);

        $response->assertSessionHasErrors('birth_date');
    }

    public function test_create_actor_invalid_url_rejected(): void
    {
        $response = $this->post('/camp', [
            'full_name' => 'Joe Taslim',
            'instagram' => 'not-a-valid-url',
        ]);

        $response->assertSessionHasErrors('instagram');
    }

    public function test_edit_and_update_actor_successfully(): void
    {
        $actor = Actor::create([
            'full_name' => 'Pevita Pearce',
            'gender' => 'Perempuan',
            'birth_place' => 'Jakarta',
            'age' => 31,
        ]);

        $editPage = $this->get("/camp/{$actor->id}/edit");
        $editPage->assertStatus(200);
        $editPage->assertSee('Edit Actor');
        $editPage->assertSee('Pevita Pearce');

        $updateResponse = $this->put("/camp/{$actor->id}", [
            'full_name' => 'Pevita Cleo Eileen Pearce',
            'gender' => 'Female',
            'birth_place' => 'Jakarta, Indonesia',
            'age' => 32,
        ]);

        $updateResponse->assertRedirect('/camp');
        $updateResponse->assertSessionHas('success', 'Actor updated successfully.');

        $this->assertDatabaseHas('actors', [
            'id' => $actor->id,
            'full_name' => 'Pevita Cleo Eileen Pearce',
            'gender' => 'Perempuan',
            'birth_place' => 'Jakarta, Indonesia',
            'age' => 32,
        ]);
    }

    public function test_multiple_face_images_upload_and_individual_delete(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
        ]);

        $facesPage = $this->get("/camp/{$actor->id}/faces");
        $facesPage->assertStatus(200);
        $facesPage->assertSee('Manage Face Images');

        // Create 3 fake valid images (.jpg, .jpeg, .png) with distinct dimensions to ensure distinct content
        $file1 = UploadedFile::fake()->image('bayu_01.jpg', 100, 100);
        $file2 = UploadedFile::fake()->image('bayu_02.jpeg', 120, 120);
        $file3 = UploadedFile::fake()->image('bayu_03.png', 140, 140);

        $uploadResponse = $this->post("/camp/{$actor->id}/faces", [
            'images' => [$file1, $file2, $file3],
        ]);

        $uploadResponse->assertRedirect("/camp/{$actor->id}/faces");
        $uploadResponse->assertSessionHas('success', 'Face images uploaded successfully.');

        $this->assertEquals(3, ActorImage::where('actor_id', $actor->id)->count());

        $firstImage = ActorImage::where('actor_id', $actor->id)->first();
        Storage::disk('public')->assertExists($firstImage->image);

        // Individual face image delete
        $deleteResponse = $this->delete("/camp/{$actor->id}/faces/{$firstImage->id}");
        $deleteResponse->assertRedirect("/camp/{$actor->id}/faces");
        $deleteResponse->assertSessionHas('success', 'Face image deleted successfully.');

        $this->assertEquals(2, ActorImage::where('actor_id', $actor->id)->count());
        Storage::disk('public')->assertMissing($firstImage->image);
    }

    public function test_delete_actor_cascades_and_removes_physical_files(): void
    {
        $actor = Actor::create([
            'full_name' => 'Actor To Delete',
            'photo' => 'sample_photo.jpg',
        ]);

        // Put a fake primary photo on disk
        Storage::disk('public')->put('actors/sample_photo.jpg', 'fake-photo-content');

        // Add 2 face images
        $faceFile1 = UploadedFile::fake()->image('face1.jpg');
        $faceFile2 = UploadedFile::fake()->image('face2.png');
        $this->post("/camp/{$actor->id}/faces", ['images' => [$faceFile1, $faceFile2]]);

        $this->assertEquals(2, ActorImage::where('actor_id', $actor->id)->count());
        $faceRecord = ActorImage::where('actor_id', $actor->id)->first();
        Storage::disk('public')->assertExists($faceRecord->image);

        // Delete actor
        $deleteResponse = $this->delete("/camp/{$actor->id}");
        $deleteResponse->assertRedirect('/camp');
        $deleteResponse->assertSessionHas('success', 'Actor deleted successfully.');

        $this->assertDatabaseMissing('actors', ['id' => $actor->id]);
        $this->assertEquals(0, ActorImage::where('actor_id', $actor->id)->count());

        // Assert physical files deleted from storage
        Storage::disk('public')->assertMissing('sample_photo.jpg');
        Storage::disk('public')->assertMissing($faceRecord->image);
    }

    public function test_camp_search_and_pagination(): void
    {
        Actor::create(['full_name' => 'Bayu Eko Moektito']);
        Actor::create(['full_name' => 'Bayu Airlangga']);
        Actor::create(['full_name' => 'Iqbaal Ramadhan']);

        // Search Bayu
        $searchRes = $this->get('/camp?search=Bayu');
        $searchRes->assertStatus(200);
        $searchRes->assertSee('Bayu Eko Moektito');
        $searchRes->assertSee('Bayu Airlangga');
        $searchRes->assertDontSee('Iqbaal Ramadhan');

        // Pagination rows per page
        $pageRes = $this->get('/camp?per_page=5');
        $pageRes->assertStatus(200);
    }

    public function test_actor_detail_renders_filmography_from_database(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
            'birth_date' => '1993-11-13',
            'age' => 31,
            'birth_place' => 'Malang',
            'biography' => 'Actor and director.',
        ]);

        $movie = Movie::create([
            'title' => 'Yowis Ben',
            'release_year' => 2018,
            'genre' => 'Comedy',
        ]);

        Character::create([
            'actor_id' => $actor->id,
            'movie_id' => $movie->id,
            'character_name' => 'Bayu',
        ]);

        $detailRes = $this->get("/actors/{$actor->id}");
        $detailRes->assertStatus(200);
        $detailRes->assertSee('Bayu Eko Moektito');
        $detailRes->assertSee('Male'); // English gender
        $detailRes->assertSee('31 Years Old'); // English age
        $detailRes->assertSee('Filmography & Roles');
        $detailRes->assertSee('Yowis Ben');
        $detailRes->assertSee('Role: Bayu');
        $detailRes->assertSee('2018');
    }

    public function test_recognition_actor_lookup_api(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
            'age' => 31,
            'birth_date' => '1993-11-13',
            'birth_place' => 'Malang',
        ]);

        // Known actor lookup (Bayu -> Bayu Eko Moektito -> DB found -> correct Actor ID)
        $knownRes = $this->get('/api/actors/lookup?name=Bayu%20Eko%20Moektito');
        $knownRes->assertStatus(200);
        $knownRes->assertJson([
            'found' => true,
            'actor' => [
                'id' => $actor->id,
                'full_name' => 'Bayu Eko Moektito',
                'gender' => 'Male',
                'age' => 31,
            ],
        ]);

        // Case-insensitive lookup
        $caseRes = $this->get('/api/actors/lookup?name=bayu%20eko%20moektito');
        $caseRes->assertStatus(200);
        $caseRes->assertJson(['found' => true]);

        // Alias 'Bayu Skak' is NOT matched as full_name (no alias mechanism)
        $aliasRes = $this->get('/api/actors/lookup?name=Bayu%20Skak');
        $aliasRes->assertStatus(200);
        $aliasRes->assertJson(['found' => false, 'actor' => null]);

        // Other person / Unknown actor -> Unknown
        $otherRes = $this->get('/api/actors/lookup?name=Unknown%20Person');
        $otherRes->assertStatus(200);
        $otherRes->assertJson(['found' => false, 'actor' => null]);

        $unknownRes = $this->get('/api/actors/lookup?name=Tidak%20Dikenali');
        $unknownRes->assertStatus(200);
        $unknownRes->assertJson(['found' => false, 'actor' => null]);

        // Empty name
        $emptyRes = $this->get('/api/actors/lookup?name=');
        $emptyRes->assertStatus(200);
        $emptyRes->assertJson(['found' => false, 'actor' => null]);
    }

    public function test_active_actor_detection_with_official_identity(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
        ]);

        // When Python sends recognized identity 'Bayu Eko Moektito'
        $response = $this->postJson('/api/actors/active', [
            'actors' => ['Bayu Eko Moektito'],
            'window_title' => 'Sekawan Limo',
        ]);
        $response->assertStatus(200);

        $this->assertDatabaseHas('actors', [
            'id' => $actor->id,
            'is_detected' => true,
        ]);

        // Polling returns official identity
        $getActiveRes = $this->get('/api/actors/active');
        $getActiveRes->assertStatus(200);
        $getActiveRes->assertJsonFragment(['Bayu Eko Moektito']);

        // When unrecognized person is sent
        $responseUnknown = $this->postJson('/api/actors/active', [
            'actors' => ['Tidak Dikenali'],
            'window_title' => 'Sekawan Limo',
        ]);
        $responseUnknown->assertStatus(200);

        $this->assertDatabaseHas('actors', [
            'id' => $actor->id,
            'is_detected' => false,
        ]);
    }
}
