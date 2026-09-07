import https from 'node:https';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const certDir = path.join(__dirname, 'certs');
const serverKey = fs.readFileSync(path.join(certDir, 'server.key'));
const serverCert = fs.readFileSync(path.join(certDir, 'server.crt'));
const caCert = fs.readFileSync(path.join(certDir, 'ca.crt'));

const LARAVEL_PORT = 8001; // Internal HTTP port for php artisan serve
const HTTPS_PORT = 8000;   // Public HTTPS port for IndoLens
const HTTP_HELP_PORT = 8080; // Helper HTTP port for certificate download & redirect

/**
 * Handle direct CA certificate download
 */
function handleCaDownload(res) {
    res.writeHead(200, {
        'Content-Type': 'application/x-x509-ca-cert',
        'Content-Disposition': 'attachment; filename="indolens-ca.crt"',
        'Content-Length': caCert.length,
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'no-cache',
    });
    res.end(caCert);
}

/**
 * Proxy request to internal Laravel HTTP server
 */
function proxyToLaravel(req, res) {
    const options = {
        hostname: '127.0.0.1',
        port: LARAVEL_PORT,
        path: req.url,
        method: req.method,
        headers: {
            ...req.headers,
            'x-forwarded-for': req.socket.remoteAddress,
            'x-forwarded-proto': 'https',
            'x-forwarded-port': String(HTTPS_PORT),
            'x-forwarded-host': req.headers.host || '192.168.20.212:8000',
        }
    };

    const proxyReq = http.request(options, (proxyRes) => {
        // Forward headers
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
        console.error('[HTTPS Proxy Error]', err.message);
        if (!res.headersSent) {
            res.writeHead(502, { 'Content-Type': 'text/plain' });
            res.end('Bad Gateway: Laravel application is not reachable on port ' + LARAVEL_PORT);
        }
    });

    req.pipe(proxyReq, { end: true });
}

// 1. Primary HTTPS Server (Port 8000)
const httpsServer = https.createServer({
    key: serverKey,
    cert: serverCert,
}, (req, res) => {
    const urlPath = req.url.split('?')[0];

    // Dedicated CA certificate download routes
    if (urlPath === '/ca.crt' || urlPath === '/indolens-ca.crt') {
        return handleCaDownload(res);
    }

    // Proxy everything else to Laravel
    proxyToLaravel(req, res);
});

httpsServer.listen(HTTPS_PORT, '0.0.0.0', () => {
    console.log(`[HTTPS Server] Listening securely at https://0.0.0.0:${HTTPS_PORT}`);
    console.log(`[HTTPS Server] LAN URL   : https://192.168.20.212:${HTTPS_PORT}/camera`);
    console.log(`[HTTPS Server] Local URL : https://localhost:${HTTPS_PORT}/camera`);
});

// 2. Helper HTTP Server (Port 8080) for easy 1-click CA download & redirect
const httpServer = http.createServer((req, res) => {
    const urlPath = req.url.split('?')[0];

    if (urlPath === '/ca.crt' || urlPath === '/indolens-ca.crt') {
        return handleCaDownload(res);
    }

    // Redirect any HTTP request to the HTTPS endpoint
    const hostHeader = (req.headers.host || '').split(':')[0] || '192.168.20.212';
    res.writeHead(301, {
        'Location': `https://${hostHeader}:${HTTPS_PORT}${req.url}`
    });
    res.end();
});

httpServer.listen(HTTP_HELP_PORT, '0.0.0.0', () => {
    console.log(`[HTTP Helper] Listening at http://0.0.0.0:${HTTP_HELP_PORT} (CA download: http://192.168.20.212:${HTTP_HELP_PORT}/ca.crt)`);
});
