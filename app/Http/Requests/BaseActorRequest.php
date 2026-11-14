<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

abstract class BaseActorRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Actor primary key to ignore in unique validation (null on create).
     */
    protected function ignoreActorId(): ?int
    {
        return null;
    }

    public function rules(): array
    {
        $uniqueRule = Rule::unique('actors', 'full_name');
        if ($ignoreId = $this->ignoreActorId()) {
            $uniqueRule = $uniqueRule->ignore($ignoreId);
        }

        return [
            'full_name' => [
                'required',
                'string',
                'max:255',
                'regex:/^[a-zA-Z\s\.\'\-]+$/',
                $uniqueRule,
            ],
            'gender' => [
                'nullable',
                'string',
                'in:Male,Female,Laki-laki,Perempuan',
            ],
            'birth_date' => [
                'nullable',
                'date',
                'before_or_equal:today',
            ],
            'birth_place' => [
                'nullable',
                'string',
                'max:255',
            ],
            'age' => [
                'nullable',
                'integer',
                'min:0',
                'max:150',
            ],
            'biography' => [
                'nullable',
                'string',
            ],
            'instagram' => [
                'nullable',
                'url',
                'max:255',
            ],
            'wikipedia' => [
                'nullable',
                'url',
                'max:255',
            ],
            'imdb' => [
                'nullable',
                'url',
                'max:255',
            ],
            'photo' => [
                'nullable',
                'file',
                'image',
                'mimes:jpg,jpeg,png',
            ],
        ];
    }

    public function messages(): array
    {
        return [
            'full_name.required' => 'The actor full name is required.',
            'full_name.regex' => 'The full name must only contain letters, spaces, hyphens, apostrophes, and periods (no numbers).',
            'full_name.unique' => 'Actor already exists.',
            'birth_date.before_or_equal' => 'The birth date cannot be in the future.',
            'birth_date.date' => 'The birth date must be a valid date.',
            'instagram.url' => 'Please provide a valid URL for Instagram.',
            'wikipedia.url' => 'Please provide a valid URL for Wikipedia.',
            'imdb.url' => 'Please provide a valid URL for IMDb.',
            'photo.image' => 'The profile photo must be a valid image.',
            'photo.mimes' => 'The profile photo must be a file of type: .jpg, .jpeg, .png.',
        ];
    }
}
