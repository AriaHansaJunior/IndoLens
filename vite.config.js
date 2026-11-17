import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import { bunny } from 'laravel-vite-plugin/fonts';
import tailwindcss from '@tailwindcss/vite';
import fs from 'node:fs';
import { getPrimaryLanIp } from './generate-certs.js';

const lanIp = getPrimaryLanIp();

export default defineConfig({
    plugins: [
        laravel({
            input: [
                'resources/css/app.css', 
                'resources/js/app.js',
                'resources/css/actors.css',
                'resources/js/actors.js',
                'resources/css/actor-detail.css',
                'resources/js/actor-detail.js',
                'resources/css/camera.css',
                'resources/js/camera.js',
                'resources/css/camp.css',
                'resources/js/camp.js'
            ],
            refresh: true,
            fonts: [
                bunny('Instrument Sans', {
                    weights: [400, 500, 600],
                }),
            ],
        }),
        tailwindcss(),
    ],
    server: {
        host: '0.0.0.0',
        port: 5173,
        strictPort: true,
        cors: true,
        https: {
            key: fs.readFileSync('./certs/server.key'),
            cert: fs.readFileSync('./certs/server.crt'),
        },
        hmr: {
            host: lanIp,
        },
        watch: {
            ignored: ['**/storage/framework/views/**'],
        },
    },
});
