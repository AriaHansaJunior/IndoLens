<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('actor_roles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('actor_id')->constrained('actors')->onDelete('cascade');
            $table->string('movie_keywords'); // e.g. "sekawan limo"
            $table->string('character_name'); // e.g. "Bagas"
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('actor_roles');
    }
};
