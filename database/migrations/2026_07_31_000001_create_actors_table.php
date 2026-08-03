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
        Schema::create('actors', function (Blueprint $table) {
            $table->id();
            $table->string('full_name');
            $table->date('birth_date')->nullable();
            $table->string('birth_place')->nullable();
            $table->integer('age')->nullable();
            $table->string('gender')->nullable();
            $table->string('photo')->nullable();
            $table->text('biography')->nullable();
            $table->string('instagram')->nullable();
            $table->string('wikipedia')->nullable();
            $table->string('imdb')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('actors');
    }
};
