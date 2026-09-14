<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateActorRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     */
    public function rules(): array
    {
        $actorId = $this->route('id');

        return [
            'full_name' => [
                'required',
                'string',
                'max:255',
                'regex:/^[a-zA-Z\s\.\'\-]+$/',
                Rule::unique('actors', 'full_name')->ignore($actorId),
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

    /**
     * Custom messages for validation errors.
     */
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
