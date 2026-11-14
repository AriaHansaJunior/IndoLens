<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;

return new class extends Migration
// hai
{
    private array $tables = [
        'actors',
        'actor_images',
        'movies',
        'characters',
        'actor_roles',
    ];

    /**
     * Run the migrations.
     */
    public function up(): void
    {
        foreach ($this->tables as $tableName) {
            if (!Schema::hasColumn($tableName, 'uuid')) {
                Schema::table($tableName, function (Blueprint $table) {
                    $table->uuid('uuid')->nullable()->unique()->after('id');
                });
            }

            $rows = DB::table($tableName)->whereNull('uuid')->pluck('id');
            foreach ($rows as $rowId) {
                DB::table($tableName)
                    ->where('id', $rowId)
                    ->update(['uuid' => (string) Str::uuid()]);
            }
        }
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        foreach ($this->tables as $tableName) {
            if (Schema::hasColumn($tableName, 'uuid')) {
                Schema::table($tableName, function (Blueprint $table) use ($tableName) {
                    $table->dropUnique("{$tableName}_uuid_unique");
                    $table->dropColumn('uuid');
                });
            }
        }
    }
};
