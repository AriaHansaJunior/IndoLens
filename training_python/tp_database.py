# hanya untuk keperluan training python local, tidak dirun di web
"""
tp_database.py — Koneksi MySQL strictly read-only untuk membaca metadata aktor & gambar.

Kebijakan Keamanan & Read-Only:
1. Membaca konfigurasi dari environment variables atau Laravel .env secara lokal.
2. Tidak pernah mencetak password, app key, atau rahasia lainnya ke console/log.
3. Mendukung password kosong (default Laragon) tanpa meminta perubahan password.
4. Menjalankan 'SET SESSION TRANSACTION READ ONLY' dan 'START TRANSACTION READ ONLY'.
5. Hanya menjalankan query SELECT (parameterized queries).
6. Menutup cursor dan koneksi secara andal di blok finally.
"""

import os
import re
try:
    from tp_config import LARAVEL_ENV_FILE
except ImportError:
    from .tp_config import LARAVEL_ENV_FILE


def parse_laravel_env(env_path) -> Dict[str, str]:
    """Membaca variabel DB_* dari file .env Laravel tanpa memuat rahasia lain."""
    config = {}
    if not env_path or not os.path.exists(env_path):
        return config

    db_pattern = re.compile(r"^(DB_[A-Z0-9_]+)=(.*)$")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = db_pattern.match(line)
                if match:
                    key = match.group(1)
                    val = match.group(2).strip()
                    # Bersihkan quotes pembungkus jika ada
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    config[key] = val
    except Exception as e:
        print(f"[WARN] Tidak dapat membaca file .env: {e}")
    return config


def get_db_credentials() -> Dict[str, Any]:
    """
    Mengambil konfigurasi database MySQL.
    Prioritas: Environment Variable OS -> File Laravel .env -> Default lokal aman.
    """
    env_vars = parse_laravel_env(LARAVEL_ENV_FILE)

    host = os.environ.get("DB_HOST", env_vars.get("DB_HOST", "127.0.0.1"))
    port_str = os.environ.get("DB_PORT", env_vars.get("DB_PORT", "3306"))
    database = os.environ.get("DB_DATABASE", env_vars.get("DB_DATABASE", "indolens"))
    user = os.environ.get("DB_USERNAME", env_vars.get("DB_USERNAME", "root"))
    # Password default kosong jika tidak dispesifikasikan (sesuai setting Laragon)
    password = os.environ.get("DB_PASSWORD", env_vars.get("DB_PASSWORD", ""))

    try:
        port = int(port_str)
    except ValueError:
        port = 3306

    return {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
    }


def get_readonly_connection():
    """
    Membuka koneksi MySQL dan menegakkan sesi READ ONLY.
    Jika gagal atau driver mysql-connector-python belum terinstall, melempar exception jelas.
    """
    try:
        import mysql.connector
    except ImportError as e:
        raise RuntimeError(
            "Driver 'mysql-connector-python' belum terpasang di kernel ini.\n"
            "Jalankan di terminal/Jupyter: pip install mysql-connector-python"
        ) from e

    creds = get_db_credentials()
    try:
        conn = mysql.connector.connect(
            host=creds["host"],
            port=creds["port"],
            database=creds["database"],
            user=creds["user"],
            password=creds["password"],
            autocommit=False,
            connection_timeout=10,
        )
    except mysql.connector.Error as err:
        # Laporkan error nyata tanpa membocorkan password
        raise RuntimeError(
            f"Gagal menghubungkan ke MySQL (host={creds['host']}, port={creds['port']}, "
            f"db={creds['database']}, user={creds['user']}): {err}"
        ) from err

    # Terapkan read-only session & transaction
    cursor = conn.cursor()
    try:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute("START TRANSACTION READ ONLY")
    finally:
        cursor.close()

    return conn


def fetch_actor_image_records() -> List[Dict[str, Any]]:
    """
    Membaca seluruh relasi actors -> actor_images dari MySQL.
    Mengembalikan list of dict:
    [
        {
            "actor_id": 1,
            "full_name": "Bayu Eko Moektito",
            "image_id": 1,
            "relative_image_path": "actor-images/1-bayu-skak/bayu-skak-01.jpg"
        },
        ...
    ]
    """
    conn = get_readonly_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT
            a.id AS actor_id,
            a.full_name,
            ai.id AS image_id,
            ai.image AS relative_image_path
        FROM actors a
        INNER JOIN actor_images ai ON ai.actor_id = a.id
        ORDER BY a.id ASC, ai.id ASC
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def fetch_registered_actors() -> List[Dict[str, Any]]:
    """Membaca daftar aktor terdaftar di MySQL (id, full_name)."""
    conn = get_readonly_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, full_name FROM actors ORDER BY id ASC"
    try:
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()
