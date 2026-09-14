import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import { bunny } from 'laravel-vite-plugin/fonts';
import tailwindcss from '@tailwindcss/vite';
import os from 'node:os';
import fs from 'node:fs';

/**
 * Automatically determine laptop LAN IPv4 address for local network device access (e.g. smartphone)
 */
function getLanIp() {
    if (process.env.VITE_DEV_SERVER_HOST) {
        return process.env.VITE_DEV_SERVER_HOST;
    }
    const interfaces = os.networkInterfaces();
    for (const devName of Object.keys(interfaces)) {
        const iface = interfaces[devName];
        if (!iface) continue;
        for (const alias of iface) {
            if (alias.family === 'IPv4' && !alias.internal) {
                return alias.address;
            }
        }
    }
    return '192.168.20.212';
}

const lanIp = getLanIp();

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
