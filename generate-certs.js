import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const certDir = path.join(__dirname, 'certs');
if (!fs.existsSync(certDir)) {
    fs.mkdirSync(certDir, { recursive: true });
}

const openssl = '"C:\\Program Files\\Git\\usr\\bin\\openssl.exe"';

console.log('Generating IndoLens Local Root CA...');
execSync(`${openssl} genrsa -out "${path.join(certDir, 'ca.key')}" 2048`, { stdio: 'inherit' });
execSync(`${openssl} req -x509 -new -nodes -key "${path.join(certDir, 'ca.key')}" -sha256 -days 3650 -out "${path.join(certDir, 'ca.crt')}" -subj "/CN=IndoLens Local CA/O=IndoLens/C=ID"`, { stdio: 'inherit' });

console.log('Generating Server Key and CSR with SAN...');
execSync(`${openssl} genrsa -out "${path.join(certDir, 'server.key')}" 2048`, { stdio: 'inherit' });

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
CN = 192.168.20.212

[req_ext]
subjectAltName = @alt_names

[alt_names]
IP.1 = 192.168.20.212
IP.2 = 127.0.0.1
DNS.1 = localhost
DNS.2 = indolens.test
`;

const cnfPath = path.join(certDir, 'openssl.cnf');
fs.writeFileSync(cnfPath, cnfContent);

execSync(`${openssl} req -new -key "${path.join(certDir, 'server.key')}" -out "${path.join(certDir, 'server.csr')}" -config "${cnfPath}"`, { stdio: 'inherit' });

console.log('Signing Server Certificate with Local CA...');
execSync(`${openssl} x509 -req -in "${path.join(certDir, 'server.csr')}" -CA "${path.join(certDir, 'ca.crt')}" -CAkey "${path.join(certDir, 'ca.key')}" -CAcreateserial -out "${path.join(certDir, 'server.crt')}" -days 825 -sha256 -extfile "${cnfPath}" -extensions req_ext`, { stdio: 'inherit' });

console.log('Verifying generated certificates in certs directory:');
const files = fs.readdirSync(certDir);
console.log(files);
console.log('Certificate generation complete!');
