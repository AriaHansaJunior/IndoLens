# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 06: INTEGRASI REFERENCE DATA (KE WEB)
 Shell 06 di Jupyter Notebook
 
 Fungsi:
 1. Membaca daftar embedding yang lolos validasi dari Stage 05.
 2. Menyiapkan staging area terisolasi: artifacts/06_integrasi_reference_data/staging/.
 3. Memformat nama folder sesuai konvensi runtime: <actor_slug>/<image_id>.npy.
 4. Membuat manifest staging yang memetakan id, full_name, slug, dan file .npy.
 5. Membuat backup aman dari folder runtime python/embeddings/ sebelum perubahan.
 6. Mempromosikan data dari staging ke python/embeddings/ secara aman:
    - Tidak menghapus aktor terdaftar lain.
    - Menjamin semua file berukuran tepat 128 dimensi float32.
 7. Opsional: Memanggil sinyal reload (POST /reload-embeddings) ke yolo_service jika sedang aktif.
 8. Tidak mengubah database MySQL sama sekali.
========================================================================================
"""

import os
import sys
import re
import json
import time
import shutil
from pathlib import Path
import urllib.request
import numpy as np

_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
for _p in [_ROOT, _ROOT / "training_python", _ROOT / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    import tp_config as cfg
    from tp_manifest_utils import load_manifest, save_manifest_atomic
except ImportError:
    from training_python import tp_config as cfg
    from training_python.tp_manifest_utils import load_manifest, save_manifest_atomic


def slugify_actor_name(full_name: str) -> str:
    """Mengubah nama aktor menjadi slug standar IndoLens (e.g. 'Bayu Eko Moektito' -> 'bayu_eko_moektito')."""
    return re.sub(r'[^a-zA-Z0-9]+', '_', full_name).lower().strip('_')


def trigger_service_reload():
    """Mengirim sinyal reload memori ke yolo_service jika berjalan di port 8002."""
    url = f"{cfg.SERVICE_URL}/reload-embeddings"
    try:
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                return True, body
            return False, f"HTTP Status {resp.status}"
    except Exception as e:
        return False, f"Microservice tidak aktif atau tidak dapat dijangkau: {e}"


def run_stage_06(promote_to_production: bool = True):
    """
    Eksekusi Stage 06: Integrasi Reference Data ke Web IndoLens.
    
    :param promote_to_production: Jika True, salin hasil staging ke python/embeddings/.
    """
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 06: INTEGRASI REFERENCE DATA KE SISTEM WEB INDOLENS")
    print("=" * 75)

    if not cfg.STAGE05_VALID_LIST.exists():
        raise FileNotFoundError(
            f"Daftar embedding tervalidasi tidak ditemukan di: {cfg.STAGE05_VALID_LIST}\n"
            "Jalankan Stage 05 terlebih dahulu."
        )

    with open(cfg.STAGE05_VALID_LIST, "r", encoding="utf-8") as f:
        valid_items = json.load(f)

    if not valid_items:
        raise RuntimeError(
            f"Daftar embedding tervalidasi kosong ({cfg.STAGE05_VALID_LIST}).\n"
            "Tidak ada embedding yang lolos validasi Stage 05. Promosi ke production dibatalkan."
        )

    print(f"[*] Memuat {len(valid_items)} vektor embedding terverifikasi dari Stage 05.")

    # 1. Bersihkan staging folder
    if cfg.STAGE06_STAGING_DIR.exists():
        shutil.rmtree(cfg.STAGE06_STAGING_DIR, ignore_errors=True)
    cfg.STAGE06_STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Kelompokkan per aktor & salin ke staging
    actors_map = {}
    staged_count = 0

    for item in valid_items:
        image_id = item["image_id"]
        actor_id = item["actor_id"]
        full_name = item["full_name"]
        src_path = Path(item["vector_path"])

        slug = slugify_actor_name(full_name)
        if slug not in actors_map:
            actors_map[slug] = {
                "actor_id": actor_id,
                "full_name": full_name,
                "slug": slug,
                "files": [],
            }

        dest_dir = cfg.STAGE06_STAGING_DIR / slug
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"{image_id}.npy"

        # Salin dan verifikasi matematis ketat
        shutil.copy2(src_path, dest_file)
        vec_check = np.load(str(dest_file))
        if vec_check.shape != (cfg.EMBEDDING_DIM,):
            raise ValueError(f"Dimensi vektor tidak valid pada {dest_file.name}: {vec_check.shape}")
        if np.isnan(vec_check).any() or np.isinf(vec_check).any():
            raise ValueError(f"Vektor mengandung NaN atau Inf pada {dest_file.name}")
        norm = float(np.linalg.norm(vec_check))
        if abs(norm - 1.0) > cfg.L2_NORM_TOLERANCE:
            raise ValueError(f"L2 norm vektor menyimpang ({norm:.6f}) pada {dest_file.name}")

        actors_map[slug]["files"].append(f"{image_id}.npy")
        staged_count += 1

    if staged_count == 0 or not actors_map:
        raise RuntimeError("Tidak ada vektor embedding valid yang berhasil disiapkan di staging. Promosi dibatalkan.")

    # Urutkan daftar file per aktor
    for slug in actors_map:
        actors_map[slug]["files"] = sorted(actors_map[slug]["files"])

    staging_manifest = {
        "actors": actors_map,
        "updated_at": time.time(),
        "total_staged_embeddings": staged_count,
    }
    with open(cfg.STAGE06_STAGING_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(staging_manifest, f, indent=2)

    print(f"[OK] Staging selesai: {staged_count} vektor untuk {len(actors_map)} aktor di:\n    {cfg.STAGE06_STAGING_DIR}")

    if not promote_to_production:
        print("[!] promote_to_production=False. Staging dibuat namun tidak disalin ke runtime.")
        return {"status": "staged_only", "staged_count": staged_count}

    # 3. Buat Backup Folder Runtime python/embeddings/
    backup_timestamp = int(time.time())
    backup_target = cfg.STAGE06_BACKUP_DIR / f"backup_{backup_timestamp}"
    if cfg.PRODUCTION_EMBEDDINGS_DIR.exists():
        print(f"[*] Membuat backup folder runtime ke: {backup_target}")
        shutil.copytree(cfg.PRODUCTION_EMBEDDINGS_DIR, backup_target)
    else:
        cfg.PRODUCTION_EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Promosi Staging ke Production
    #    - Folder aktor yang diintegrasi dibuat PERSIS sama dengan set tervalidasi:
    #      file .npy lama yang tidak lolos validasi (mis. gambar multi-face / zero-face /
    #      gambar yang sudah dihapus di CAMP) dibuang dari runtime agar tidak ikut dicocokkan.
    #    - Folder aktor lain yang tidak ada di run ini TIDAK disentuh.
    #    - Backup lengkap sudah dibuat di langkah 3 sebelum perubahan apa pun.
    prod_manifest = load_manifest(cfg.PRODUCTION_MANIFEST)
    prod_actors = prod_manifest.get("actors", {}) if isinstance(prod_manifest, dict) else {}
    pruned_stale = {}

    for slug, info in actors_map.items():
        prod_actor_dir = cfg.PRODUCTION_EMBEDDINGS_DIR / slug
        prod_actor_dir.mkdir(parents=True, exist_ok=True)
        validated = set(info["files"])

        # Salin file .npy tervalidasi
        for fname in info["files"]:
            shutil.copy2(cfg.STAGE06_STAGING_DIR / slug / fname, prod_actor_dir / fname)

        # Buang embedding stale yang tidak lolos validasi pipeline ini
        stale = sorted(f.name for f in prod_actor_dir.glob("*.npy") if f.name not in validated)
        for fname in stale:
            (prod_actor_dir / fname).unlink()
        if stale:
            pruned_stale[slug] = stale
            print(f"[*] {info['full_name']}: {len(stale)} embedding stale dibuang dari runtime -> {stale}")

        active = sorted(f.name for f in prod_actor_dir.glob("*.npy"))
        if set(active) != validated:
            raise RuntimeError(f"Verifikasi gagal untuk {slug}: runtime={active}, validated={sorted(validated)}")

        prod_actors[slug] = {
            "actor_id": info["actor_id"],
            "full_name": info["full_name"],
            "slug": slug,
            "files": active,
        }

    # Baca optimal threshold dari Stage 05 jika ada
    optimal_th = cfg.DEFAULT_FALLBACK_THRESHOLD
    calib_method = "DEFAULT"
    if cfg.STAGE05_OPTIMAL_THRESHOLD_JSON.exists():
        try:
            with open(cfg.STAGE05_OPTIMAL_THRESHOLD_JSON, "r", encoding="utf-8") as f:
                th_data = json.load(f)
                optimal_th = th_data.get("optimal_threshold", optimal_th)
                calib_method = th_data.get("calibration_method", calib_method)
        except Exception:
            pass

    # Simpan manifest baru di production
    prod_manifest_data = {
        "actors": prod_actors,
        "optimal_threshold": optimal_th,
        "calibration_method": calib_method,
        "embedding_dim": cfg.PRIMARY_EMBEDDING_DIM,
        "updated_at": time.time(),
    }
    save_manifest_atomic(cfg.PRODUCTION_MANIFEST, prod_manifest_data)
    print(f"[OK] Berhasil dipromosikan ke runtime: {cfg.PRODUCTION_EMBEDDINGS_DIR}")
    print(f"[OK] Threshold runtime diselaraskan : {optimal_th} ({calib_method})")
    print(f"[OK] Dimensi embedding diselaraskan : {cfg.PRIMARY_EMBEDDING_DIM}-D")

    # Update python/config/dataset.py jika ada
    runtime_dataset_cfg = cfg.PROJECT_ROOT / "python" / "config" / "dataset.py"
    if runtime_dataset_cfg.exists():
        try:
            content = runtime_dataset_cfg.read_text(encoding="utf-8")
            content = re.sub(r'FACENET_EMBEDDING_DIM\s*=\s*\d+', f'FACENET_EMBEDDING_DIM = {cfg.PRIMARY_EMBEDDING_DIM}', content)
            content = re.sub(r'FACE_DISTANCE_THRESHOLD\s*=\s*[0-9.]+', f'FACE_DISTANCE_THRESHOLD = {optimal_th}', content)
            runtime_dataset_cfg.write_text(content, encoding="utf-8")
            print(f"[OK] python/config/dataset.py diselaraskan (DIM={cfg.PRIMARY_EMBEDDING_DIM}, TH={optimal_th})")
        except Exception as e:
            print(f"[!] Warning update dataset.py: {e}")

    # 5. Opsional Sinyal Reload ke Microservice
    reload_success, reload_detail = trigger_service_reload()
    if reload_success:
        print(f"[OK] Sinyal reload memori berhasil diterima yolo_service: {reload_detail}")
    else:
        print(f"[-] Catatan reload runtime: {reload_detail}")
        print("    (Normal jika yolo_service sedang tidak berjalan. Saat dijalankan nanti, sistem akan membaca otomatis).")

    integration_report = {
        "integrated_at": time.time(),
        "staged_count": staged_count,
        "actors_integrated": list(actors_map.keys()),
        "pruned_stale_embeddings": pruned_stale,
        "backup_location": str(backup_target) if backup_target.exists() else None,
        "production_target": str(cfg.PRODUCTION_EMBEDDINGS_DIR),
        "service_reload_success": reload_success,
        "service_reload_detail": reload_detail,
    }

    with open(cfg.STAGE06_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(integration_report, f, indent=2)

    print("\n" + "=" * 75)
    print("  INTEGRASI SELESAI")
    print(f"  Total Vektor Aktif : {staged_count}")
    print(f"  Target Runtime     : {cfg.PRODUCTION_EMBEDDINGS_DIR}")
    print(f"  Laporan Integrasi  : {cfg.STAGE06_REPORT_JSON}")
    print("=" * 75)

    return integration_report


if __name__ == "__main__":
    run_stage_06()
