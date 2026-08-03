<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class HomeController extends Controller
{
    /**
     * Display the main IndoLens interface.
     */
    public function index()
    {
        return view('home');
    }
}
