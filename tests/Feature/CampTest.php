<?php

namespace Tests\Feature;

use App\Models\Actor;
use App\Models\ActorImage;
use App\Models\ActorRole;
use App\Models\Character;
use App\Models\Movie;
use Carbon\Carbon;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
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
        Http::fake([
            'http://127.0.0.1:8002/*' => Http::response(['status' => 'success', 'generated_count' => 1], 200),
        ]);
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

        $editPage = $this->get("/camp/{$actor->uuid}/edit");
        $editPage->assertStatus(200);
        $editPage->assertSee('Edit Actor');
        $editPage->assertSee('Pevita Pearce');

        $updateResponse = $this->put("/camp/{$actor->uuid}", [
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

        $facesPage = $this->get("/camp/{$actor->uuid}/faces");
        $facesPage->assertStatus(200);
        $facesPage->assertSee('Manage Face Images');

        // Create 3 fake valid images (.jpg, .jpeg, .png) with distinct dimensions to ensure distinct content
        $file1 = UploadedFile::fake()->image('bayu_01.jpg', 100, 100);
        $file2 = UploadedFile::fake()->image('bayu_02.jpeg', 120, 120);
        $file3 = UploadedFile::fake()->image('bayu_03.png', 140, 140);

        $uploadResponse = $this->post("/camp/{$actor->uuid}/faces", [
            'images' => [$file1, $file2, $file3],
        ]);

        $uploadResponse->assertRedirect("/camp/{$actor->uuid}/faces");
        $uploadResponse->assertSessionHas('success', 'Face images uploaded successfully.');

        $this->assertEquals(3, ActorImage::where('actor_id', $actor->id)->count());

        $firstImage = ActorImage::where('actor_id', $actor->id)->first();
        Storage::disk('public')->assertExists($firstImage->image);

        // Individual face image delete
        $deleteResponse = $this->delete("/camp/{$actor->uuid}/faces/{$firstImage->uuid}");
        $deleteResponse->assertRedirect("/camp/{$actor->uuid}/faces");
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
        $this->post("/camp/{$actor->uuid}/faces", ['images' => [$faceFile1, $faceFile2]]);

        $this->assertEquals(2, ActorImage::where('actor_id', $actor->id)->count());
        $faceRecord = ActorImage::where('actor_id', $actor->id)->first();
        Storage::disk('public')->assertExists($faceRecord->image);

        // Delete actor
        $deleteResponse = $this->delete("/camp/{$actor->uuid}");
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

        $detailRes = $this->get("/actors/{$actor->uuid}");
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

        // Known actor lookup (Bayu -> Bayu Eko Moektito -> DB found -> correct Actor UUID)
        $knownRes = $this->get('/api/actors/lookup?name=Bayu%20Eko%20Moektito');
        $knownRes->assertStatus(200);
        $knownRes->assertJson([
            'found' => true,
            'actor' => [
                'uuid' => $actor->uuid,
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

    public function test_store_faces_triggers_yolo_embedding_sync(): void
    {
        Http::fake([
            'http://127.0.0.1:8002/sync-actor-embedding' => Http::response([
                'status' => 'success',
                'generated_count' => 1,
            ], 200),
        ]);

        Storage::fake('public');

        $actor = Actor::create([
            'full_name' => 'Aktor Uji Coba',
            'gender' => 'Laki-laki',
        ]);

        $file = \Illuminate\Http\UploadedFile::fake()->image('face1.jpg', 200, 200);

        $response = $this->post(route('camp.faces.store', $actor), [
            'images' => [$file],
        ]);

        $response->assertRedirect(route('camp.faces', $actor));
        $this->assertDatabaseHas('actor_images', [
            'actor_id' => $actor->id,
        ]);

        Http::assertSent(function ($request) use ($actor) {
            return $request->url() === 'http://127.0.0.1:8002/sync-actor-embedding'
                && $request['actor_id'] === $actor->id
                && $request['full_name'] === 'Aktor Uji Coba'
                && count($request['images']) === 1;
        });
    }

    public function test_destroy_face_triggers_yolo_embedding_delete(): void
    {
        Http::fake([
            'http://127.0.0.1:8002/delete-actor-embedding' => Http::response(['status' => 'success'], 200),
        ]);

        Storage::fake('public');

        $actor = Actor::create([
            'full_name' => 'Aktor Hapus',
            'gender' => 'Perempuan',
        ]);

        $image = ActorImage::create([
            'actor_id' => $actor->id,
            'image' => 'actor-images/test/face.jpg',
        ]);

        $response = $this->delete(route('camp.faces.destroy', [$actor, $image]));
        $response->assertRedirect(route('camp.faces', $actor));

        $this->assertDatabaseMissing('actor_images', ['id' => $image->id]);

        Http::assertSent(function ($request) use ($actor, $image) {
            return $request->url() === 'http://127.0.0.1:8002/delete-actor-embedding'
                && $request['actor_id'] === $actor->id
                && $request['image_id'] === $image->id;
        });
    }

    public function test_destroy_actor_triggers_yolo_actor_delete(): void
    {
        Http::fake([
            'http://127.0.0.1:8002/delete-actor' => Http::response(['status' => 'success'], 200),
        ]);

        Storage::fake('public');

        $actor = Actor::create([
            'full_name' => 'Aktor Musnah',
            'gender' => 'Laki-laki',
        ]);

        $response = $this->delete(route('camp.destroy', $actor));
        $response->assertRedirect(route('camp.index'));

        $this->assertDatabaseMissing('actors', ['id' => $actor->id]);

        Http::assertSent(function ($request) use ($actor) {
            return $request->url() === 'http://127.0.0.1:8002/delete-actor'
                && $request['actor_id'] === $actor->id
                && $request['full_name'] === 'Aktor Musnah';
        });
    }

    public function test_plain_integer_ids_are_rejected_and_uuid_urls_succeed(): void
    {
        $actor = Actor::create([
            'full_name' => 'Joshua Suherman',
            'gender' => 'Laki-laki',
        ]);

        $this->get("/actors/{$actor->id}")->assertNotFound();
        $this->get("/camp/{$actor->id}/edit")->assertNotFound();
        $this->get("/camp/{$actor->id}/faces")->assertNotFound();

        $this->get("/actors/{$actor->uuid}")->assertStatus(200);
        $this->get("/camp/{$actor->uuid}/edit")->assertStatus(200);
        $this->get("/camp/{$actor->uuid}/faces")->assertStatus(200);
    }

    public function test_create_actor_with_profile_photo_saves_file_and_path(): void
    {
        $photo = UploadedFile::fake()->image('profile.jpg', 300, 300);

        $response = $this->post('/camp', [
            'full_name' => 'Tutus Thomson',
            'gender' => 'Male',
            'photo' => $photo,
        ]);

        $response->assertRedirect('/camp');
        $actor = Actor::where('full_name', 'Tutus Thomson')->firstOrFail();

        $this->assertNotNull($actor->photo);
        Storage::disk('public')->assertExists($actor->photo);
    }

    public function test_manage_actor_filmography_and_recognition_roles(): void
    {
        $actor = Actor::create([
            'full_name' => 'Brandon Salim',
            'gender' => 'Laki-laki',
        ]);

        $this->get(route('camp.roles', $actor))
            ->assertStatus(200)
            ->assertSee('Manage Roles & Filmography');

        // Create character with new movie inline
        $charRes = $this->post(route('camp.characters.store', $actor), [
            'new_movie_title' => 'Yowis Ben 2',
            'new_movie_year' => 2019,
            'new_movie_genre' => 'Comedy',
            'character_name' => 'Nando',
        ]);
        $charRes->assertRedirect(route('camp.roles', $actor));

        $this->assertDatabaseHas('movies', ['title' => 'Yowis Ben 2', 'release_year' => 2019]);
        $this->assertDatabaseHas('characters', [
            'actor_id' => $actor->id,
            'character_name' => 'Nando',
        ]);

        // Add live recognition keyword role
        $roleRes = $this->post(route('camp.roles.store', $actor), [
            'movie_keywords' => 'yowis ben 2, yowisben',
            'character_name' => 'Nando',
        ]);
        $roleRes->assertRedirect(route('camp.roles', $actor));

        $this->assertDatabaseHas('actor_roles', [
            'actor_id' => $actor->id,
            'movie_keywords' => 'yowis ben 2, yowisben',
            'character_name' => 'Nando',
        ]);

        $character = Character::where('actor_id', $actor->id)->firstOrFail();
        $role = ActorRole::where('actor_id', $actor->id)->firstOrFail();

        $this->delete(route('camp.characters.destroy', [$actor, $character]))
            ->assertRedirect(route('camp.roles', $actor));
        $this->assertDatabaseMissing('characters', ['id' => $character->id]);

        $this->delete(route('camp.roles.destroy', [$actor, $role]))
            ->assertRedirect(route('camp.roles', $actor));
        $this->assertDatabaseMissing('actor_roles', ['id' => $role->id]);
    }

    public function test_sync_embeddings_artisan_command(): void
    {
        Http::fake([
            'http://127.0.0.1:8002/health' => Http::response(['status' => 'ready'], 200),
            'http://127.0.0.1:8002/prune-orphaned-actors' => Http::response([
                'status' => 'success',
                'pruned_orphans' => [],
            ], 200),
            'http://127.0.0.1:8002/sync-actor-embedding' => Http::response([
                'status' => 'success',
                'generated_count' => 1,
                'total_embeddings_for_actor' => 1,
            ], 200),
            'http://127.0.0.1:8002/reload-embeddings' => Http::response([
                'status' => 'success',
                'actors_loaded' => 1,
            ], 200),
        ]);

        $this->artisan('indolens:sync-embeddings')
            ->assertExitCode(0);
    }

    public function test_prevent_duplicate_movie_character_and_role_keyword(): void
    {
        $actor = Actor::create([
            'full_name' => 'Bayu Eko Moektito',
            'gender' => 'Laki-laki',
            'age' => 33,
            'birth_date' => '1993-11-13',
            'birth_place' => 'Malang',
            'biography' => 'Indonesian actor and director.',
        ]);

        // Submit filmography character twice with different casing for new movie title
        $this->post(route('camp.characters.store', $actor), [
            'new_movie_title' => 'Yowis Ben',
            'new_movie_year' => 2018,
            'character_name' => 'Bayu',
        ])->assertRedirect(route('camp.roles', $actor));

        $this->post(route('camp.characters.store', $actor), [
            'new_movie_title' => 'yowis ben',
            'new_movie_year' => 2018,
            'character_name' => 'Bayu',
        ])->assertRedirect(route('camp.roles', $actor));

        $this->assertSame(1, Movie::count());
        $this->assertSame(1, Character::where('actor_id', $actor->id)->count());

        // Submit recognition keyword role twice with same normalized keywords
        $this->post(route('camp.roles.store', $actor), [
            'movie_keywords' => 'yowis ben',
            'character_name' => 'Bayu',
        ])->assertRedirect(route('camp.roles', $actor));

        $this->post(route('camp.roles.store', $actor), [
            'movie_keywords' => '  Yowis Ben  ',
            'character_name' => 'Bayu Updated',
        ])->assertRedirect(route('camp.roles', $actor));

        $this->assertSame(1, ActorRole::where('actor_id', $actor->id)->count());
        $this->assertDatabaseHas('actor_roles', [
            'actor_id' => $actor->id,
            'movie_keywords' => 'yowis ben',
            'character_name' => 'Bayu Updated',
        ]);
    }

    public function test_destroy_actor_cleans_up_primary_photo_even_when_outside_actor_directory(): void
    {
        Http::fake(['*' => Http::response(['status' => 'ok'], 200)]);

        Storage::disk('public')->put('actors/custom_primary.jpg', 'primary-bytes');
        Storage::disk('public')->put('actor-images/test-actor/01.jpg', 'face-bytes');

        $actor = Actor::create([
            'full_name' => 'Test Actor',
            'gender' => 'Laki-laki',
            'age' => 30,
            'birth_date' => '1996-01-01',
            'birth_place' => 'Surabaya',
            'biography' => 'Biography text.',
            'photo' => 'actors/custom_primary.jpg',
        ]);

        ActorImage::create([
            'actor_id' => $actor->id,
            'image' => 'actor-images/test-actor/01.jpg',
        ]);

        $this->delete(route('camp.destroy', $actor))
            ->assertRedirect(route('camp.index'));

        $this->assertDatabaseMissing('actors', ['id' => $actor->id]);
        Storage::disk('public')->assertMissing('actors/custom_primary.jpg');
        Storage::disk('public')->assertMissing('actor-images/test-actor/01.jpg');
    }
}
