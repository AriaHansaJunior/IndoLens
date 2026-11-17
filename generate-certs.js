import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const certDir = path.join(__dirname, 'certs');

const VIRTUAL_ADAPTER_PATTERN = /vethernet|virtualbox|vmware|hyper-v|wsl|docker|loopback|bluetooth|tailscale|zerotier|hamachi|npcap/i;
const PREFERRED_ADAPTER_PATTERN = /wi-?fi|wireless|wlan|ethernet/i;

export function getLanIps() {
    if (process.env.VITE_DEV_SERVER_HOST) {
        return [process.env.VITE_DEV_SERVER_HOST.trim()];
    }

    const interfaces = os.networkInterfaces();
    const candidates = [];

    for (const [name, entries] of Object.entries(interfaces)) {
        if (!entries) continue;

        for (const alias of entries) {
            if (alias.family !== 'IPv4' || alias.internal) continue;

            let score = 1;
            if (VIRTUAL_ADAPTER_PATTERN.test(name)) {
                score = 0;
            } else if (/^192\.168\.137\./.test(alias.address)) {
                // Prioritize Windows Mobile Hotspot subnet when active
                score = 4;
            } else if (PREFERRED_ADAPTER_PATTERN.test(name)) {
                score = 3;
            } else if (/^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[01])\./.test(alias.address)) {
                score = 2;
            }

            candidates.push({ address: alias.address, score });
        }
    }

    candidates.sort((a, b) => b.score - a.score);
    return [...new Set(candidates.map((c) => c.address))];
}

export function getPrimaryLanIp() {
    const ips = getLanIps();
    return ips[0] || '127.0.0.1';
}

function resolveOpenSslBinary() {
    const knownPaths = [
        'C:\\Program Files\\Git\\usr\\bin\\openssl.exe',
        'C:\\Program Files\\Git\\mingw64\\bin\\openssl.exe',
        'openssl',
    ];

    for (const candidate of knownPaths) {
        if (candidate === 'openssl' || fs.existsSync(candidate)) {
            return candidate;
        }
    }

    throw new Error('OpenSSL executable not found.');
}

export function generateCertificates({ resetCa = false } = {}) {
    if (!fs.existsSync(certDir)) {
        fs.mkdirSync(certDir, { recursive: true });
    }

    const openssl = resolveOpenSslBinary();
    const caKeyPath = path.join(certDir, 'ca.key');
    const caCertPath = path.join(certDir, 'ca.crt');
    const serverKeyPath = path.join(certDir, 'server.key');
    const serverCsrPath = path.join(certDir, 'server.csr');
    const serverCertPath = path.join(certDir, 'server.crt');
    const cnfPath = path.join(certDir, 'openssl.cnf');

    if (resetCa || !fs.existsSync(caKeyPath) || !fs.existsSync(caCertPath)) {
        console.log('Generating IndoLens Local Root CA...');
        execFileSync(openssl, ['genrsa', '-out', caKeyPath, '2048'], { stdio: 'inherit' });
        execFileSync(
            openssl,
            ['req', '-x509', '-new', '-nodes', '-key', caKeyPath, '-sha256', '-days', '3650', '-out', caCertPath, '-subj', '/CN=IndoLens Local CA/O=IndoLens/C=ID'],
            { stdio: 'inherit' }
        );
    } else {
        console.log('Reusing existing IndoLens Local Root CA (certs/ca.crt)...');
    }

    const lanIps = getLanIps();
    const primaryIp = lanIps[0] || '127.0.0.1';
    const altIps = [...new Set([...lanIps, '127.0.0.1'])];
    const ipLines = altIps.map((ip, idx) => `IP.${idx + 1} = ${ip}`).join('\n');

    console.log(`Generating Server Certificate for LAN IP: ${primaryIp} ...`);
    if (resetCa || !fs.existsSync(serverKeyPath)) {
        execFileSync(openssl, ['genrsa', '-out', serverKeyPath, '2048'], { stdio: 'inherit' });
    }

    const cnfContent = `[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = ID
ST = Indonesia
L = Jakarta
O = IndoLens
OU = Development
CN = ${primaryIp}

[req_ext]
subjectAltName = @alt_names

[alt_names]
${ipLines}
DNS.1 = localhost
DNS.2 = indolens.test
`;

    fs.writeFileSync(cnfPath, cnfContent);

    execFileSync(openssl, ['req', '-new', '-key', serverKeyPath, '-out', serverCsrPath, '-config', cnfPath], { stdio: 'inherit' });
    execFileSync(
        openssl,
        ['x509', '-req', '-in', serverCsrPath, '-CA', caCertPath, '-CAkey', caKeyPath, '-CAcreateserial', '-out', serverCertPath, '-days', '825', '-sha256', '-extfile', cnfPath, '-extensions', 'req_ext'],
        { stdio: 'inherit' }
    );

    console.log(`Certificates ready in ${certDir} (SAN IPs: ${altIps.join(', ')})`);
}

export function ensureCertsForCurrentLan() {
    const lanIps = getLanIps();
    const primaryIp = lanIps[0] || '127.0.0.1';
    const cnfPath = path.join(certDir, 'openssl.cnf');
    const serverCertPath = path.join(certDir, 'server.crt');
    const serverKeyPath = path.join(certDir, 'server.key');
    const caCertPath = path.join(certDir, 'ca.crt');

    if (fs.existsSync(serverCertPath) && fs.existsSync(serverKeyPath) && fs.existsSync(caCertPath) && fs.existsSync(cnfPath)) {
        const cnfText = fs.readFileSync(cnfPath, 'utf8');
        const allIpsPresent = lanIps.every((ip) =>
            new RegExp(`^IP\\.\\d+\\s*=\\s*${ip.replace(/\./g, '\\.')}\\s*$`, 'm').test(cnfText)
        );
        if (primaryIp === '127.0.0.1' || (allIpsPresent && cnfText.includes(`CN = ${primaryIp}`))) {
            return primaryIp;
        }
    }

    generateCertificates({ resetCa: false });
    return primaryIp;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(__filename);
if (isMain) {
    const resetCa = process.argv.includes('--reset-ca');
    generateCertificates({ resetCa });
}
