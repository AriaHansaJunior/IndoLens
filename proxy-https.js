import https from 'node:https';
import http from 'node:http';
import net from 'node:net';
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
const PORT = 8000;         // Public port for IndoLens (HTTPS + HTTP auto-redirect)
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
            'x-forwarded-port': String(PORT),
            'x-forwarded-host': req.headers.host || 'localhost:8000',
        }
    };

    const proxyReq = http.request(options, (proxyRes) => {
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

const VITE_PORT = 5173;

/**
 * Check if request is for Vite assets or Vite client
 */
function isViteRequest(urlPath) {
    return urlPath.startsWith('/@vite') ||
           urlPath.startsWith('/resources/') ||
           urlPath.startsWith('/@fs/') ||
           urlPath.startsWith('/@id/') ||
           urlPath.startsWith('/node_modules/') ||
           urlPath.startsWith('/__vite');
}

/**
 * Proxy asset request to Vite HTTPS dev server
 */
function proxyToVite(req, res) {
    const options = {
        hostname: '127.0.0.1',
        port: VITE_PORT,
        path: req.url,
        method: req.method,
        headers: {
            ...req.headers,
            host: `localhost:${VITE_PORT}`,
        },
        rejectUnauthorized: false,
    };

    const proxyReq = https.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
        console.error('[Vite Proxy Error]', err.message);
        if (!res.headersSent) {
            res.writeHead(502, { 'Content-Type': 'text/plain' });
            res.end('Bad Gateway: Vite server is not reachable on port ' + VITE_PORT);
        }
    });

    req.pipe(proxyReq, { end: true });
}

const YOLO_PORT = 8002;

/**
 * Proxy request to internal Python YOLO Face Detection micro-service (Session 3)
 */
function proxyToYolo(req, res) {
    const targetPath = req.url.replace(/^\/api\/yolo/, '') || '/';
    const options = {
        hostname: '127.0.0.1',
        port: YOLO_PORT,
        path: targetPath,
        method: req.method,
        headers: {
            ...req.headers,
            host: `127.0.0.1:${YOLO_PORT}`,
        }
    };

    const proxyReq = http.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
        console.error('[YOLO Proxy Error]', err.message);
        if (!res.headersSent) {
            res.writeHead(502, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'error', message: 'YOLO service is not reachable on port ' + YOLO_PORT }));
        }
    });

    req.pipe(proxyReq, { end: true });
}

// 1. Primary HTTPS Server (Handles secure TLS traffic)
const httpsServer = https.createServer({
    key: serverKey,
    cert: serverCert,
    ca: caCert,
}, (req, res) => {
    const clientIp = req.socket.remoteAddress;
    console.log(`[HTTPS Request] ${req.method} ${req.url} from ${clientIp}`);

    const urlPath = req.url.split('?')[0];

    // Dedicated CA certificate download routes
    if (urlPath === '/ca.crt' || urlPath === '/indolens-ca.crt') {
        return handleCaDownload(res);
    }

    // Proxy YOLO face detection API requests (Session 3)
    if (urlPath.startsWith('/api/yolo/')) {
        return proxyToYolo(req, res);
    }

    // Proxy Vite frontend assets
    if (isViteRequest(urlPath)) {
        return proxyToVite(req, res);
    }

    // Proxy everything else to Laravel
    proxyToLaravel(req, res);
});

httpsServer.on('tlsClientError', (err, socket) => {
    console.warn(`[TLS Client Error] ${err.message} from ${socket.remoteAddress || 'unknown'}`);
});

httpsServer.on('clientError', (err, socket) => {
    console.warn(`[Client Error] ${err.message}`);
    if (socket.writable) {
        socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
    }
});

// 2. HTTP Server (Handles plain HTTP requests & redirects to HTTPS)
const httpServer = http.createServer((req, res) => {
    const urlPath = req.url.split('?')[0];

    if (urlPath === '/ca.crt' || urlPath === '/indolens-ca.crt') {
        return handleCaDownload(res);
    }

    // Redirect any plain HTTP request to HTTPS seamlessly
    const hostHeader = (req.headers.host || '').split(':')[0] || 'localhost';
    const targetUrl = `https://${hostHeader}:${PORT}${req.url}`;
    console.log(`[HTTP -> HTTPS Redirect] ${req.method} ${req.url} from ${req.socket.remoteAddress} -> ${targetUrl}`);

    res.writeHead(302, {
        'Location': targetUrl,
        'Content-Type': 'text/plain',
    });
    res.end(`Redirecting to ${targetUrl}`);
});

httpServer.on('clientError', (err, socket) => {
    console.warn(`[HTTP Helper Client Error] ${err.message}`);
    if (socket.writable) {
        socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
    }
});

// Dedicated listener for port 8080 (plain HTTP helper)
httpServer.listen(HTTP_HELP_PORT, '0.0.0.0', () => {
    console.log(`[HTTP Helper] Listening on http://0.0.0.0:${HTTP_HELP_PORT} (CA download: http://192.168.20.212:${HTTP_HELP_PORT}/ca.crt)`);
});

// 3. Port 8000 Multiplexer (Distributes incoming TCP connections between HTTPS and HTTP)
const mainServer = net.createServer((socket) => {
    socket.once('data', (buf) => {
        socket.pause();
        if (buf.length > 0 && buf[0] === 0x16) {
            // Byte 0x16 (22) = TLS Handshake record -> Route to HTTPS server
            httpsServer.emit('connection', socket);
        } else {
            // Non-TLS (plain HTTP) -> Route to HTTP redirect server
            httpServer.emit('connection', socket);
        }
        socket.unshift(buf);
        socket.resume();
    });

    socket.on('error', (err) => {
        if (err.code !== 'ECONNRESET') {
            console.warn(`[Multiplexer Socket Error] ${err.message}`);
        }
    });
});

mainServer.listen(PORT, '0.0.0.0', () => {
    console.log(`[Gateway] Port ${PORT} active (HTTPS + HTTP auto-redirect)`);
    console.log(`[Gateway] Phone LAN HTTPS : https://192.168.20.212:${PORT}/camera`);
    console.log(`[Gateway] Laptop HTTPS    : https://localhost:${PORT}/camera`);
    console.log(`[Gateway] Laptop 127.0.0.1: https://127.0.0.1:${PORT}/camera`);
});
