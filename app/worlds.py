import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime

from flask import Blueprint, jsonify, current_app, send_file, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

worlds_bp = Blueprint("worlds", __name__, url_prefix="/api/worlds")

WORLD_TMP_PREFIX = "mcwebadmin_world_"


def _systemctl_is_active() -> str:
    """Return the stdout of ``systemctl is-active <service>``."""
    service = current_app.config["SERVICE_NAME"]
    result = subprocess.run(
        ["sudo", "systemctl", "is-active", service],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _dirname(path: str) -> str:
    """Return the final path component of *path*."""
    return os.path.basename(os.path.normpath(path))


def _folder_size_mb(path: str) -> float:
    """Recursively sum the size of all files under *path*, returning MB."""
    if not os.path.isdir(path):
        return 0.0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return round(total / (1024 * 1024), 2)


def _list_contents(path: str) -> list:
    """Return a sorted list of entries (files and dirs) under *path*.

    Each entry is a dict with ``name``, ``size_mb``, ``is_dir``, and
    ``modified`` (Unix mtime).  Returns an empty list if *path* doesn't exist.
    """
    if not os.path.isdir(path):
        return []
    entries = []
    try:
        for name in sorted(os.listdir(path), key=lambda n: n.lower()):
            full = os.path.join(path, name)
            try:
                stat = os.stat(full)
                is_dir = os.path.isdir(full)
                size = _folder_size_mb(full) if is_dir else round(stat.st_size / (1024 * 1024), 2)
                entries.append(
                    {
                        "name": name,
                        "size_mb": size,
                        "is_dir": is_dir,
                        "modified": int(stat.st_mtime),
                    }
                )
            except OSError:
                pass
    except OSError:
        pass
    return sorted(entries, key=lambda e: (not e["is_dir"], e["name"].lower()))


def _create_world_zip(target_dir: str, zip_path: str) -> None:
    """Create a ZIP of *target_dir* quickly, preserving relative paths.

    World data is typically already compressed, so storing entries without an
    extra compression pass is noticeably faster and avoids tying up a worker on
    CPU-heavy deflation for large downloads.
    """
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for dirpath, dirnames, filenames in os.walk(target_dir):
            rel_dir = os.path.relpath(dirpath, target_dir)
            if rel_dir == ".":
                rel_dir = ""

            if not dirnames and not filenames and rel_dir:
                archive.writestr(f"{rel_dir}/", "")

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                arcname = os.path.join(rel_dir, filename) if rel_dir else filename
                archive.write(file_path, arcname)


def _cleanup_stale_world_tmpdirs() -> None:
    """Remove prior world-download temp directories from the system temp dir."""
    temp_root = tempfile.gettempdir()

    try:
        with os.scandir(temp_root) as entries:
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if not entry.name.startswith(WORLD_TMP_PREFIX):
                    continue

                shutil.rmtree(entry.path, ignore_errors=True)
    except OSError:
        pass


def _find_world_root(staging_dir: str) -> str | None:
    """Return the directory that represents the world root (contains level.dat)."""
    candidates = []
    for dirpath, _dirnames, filenames in os.walk(staging_dir):
        if "level.dat" in filenames:
            rel = os.path.relpath(dirpath, staging_dir)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            candidates.append((depth, dirpath))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    min_depth = candidates[0][0]
    shallowest = [path for depth, path in candidates if depth == min_depth]

    if len(shallowest) != 1:
        return None

    return shallowest[0]


def _clear_directory_contents(path: str) -> None:
    """Remove everything inside *path* without removing *path* itself."""
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        return

    for name in os.listdir(path):
        target = os.path.join(path, name)
        if os.path.isdir(target) and not os.path.islink(target):
            shutil.rmtree(target)
        else:
            os.unlink(target)


def _ensure_group_writable_tree(path: str) -> None:
    """Best-effort chmod for world trees shared across service/game users.

    Some deployments keep the top-level world directory owned by another user
    (for example ``minecraft``), so chmod may raise ``PermissionError``.
    Upload should still succeed in that case.
    """
    for dirpath, dirnames, filenames in os.walk(path):
        try:
            os.chmod(dirpath, 0o2775)
        except PermissionError:
            pass

        for dirname in dirnames:
            try:
                os.chmod(os.path.join(dirpath, dirname), 0o2775)
            except PermissionError:
                pass

        for filename in filenames:
            try:
                os.chmod(os.path.join(dirpath, filename), 0o664)
            except PermissionError:
                pass


# ------------------------------------------------------------------ #
# Endpoints                                                            #
# ------------------------------------------------------------------ #


@worlds_bp.route("/status", methods=["GET"])
@jwt_required()
def get_status():
    active_dir = current_app.config["WORLD_ACTIVE_DIR"]
    inactive_dir = current_app.config["WORLD_INACTIVE_DIR"]

    active_exists = os.path.isdir(active_dir)
    inactive_exists = os.path.isdir(inactive_dir)

    server_running = False
    try:
        server_running = _systemctl_is_active() == "active"
    except Exception:
        pass

    # --- Disk usage for the parent of the active world directory ---
    parent_dir = os.path.dirname(active_dir)
    disk_total_mb = disk_free_mb = disk_used_mb = 0
    try:
        usage = shutil.disk_usage(parent_dir)
        disk_total_mb = round(usage.total / (1024 * 1024), 2)
        disk_used_mb = round(usage.used / (1024 * 1024), 2)
        disk_free_mb = round(usage.free / (1024 * 1024), 2)
    except OSError:
        pass

    return jsonify(
        {
            "active_exists": active_exists,
            "inactive_exists": inactive_exists,
            "active_size_mb": _folder_size_mb(active_dir) if active_exists else 0.0,
            "inactive_size_mb": _folder_size_mb(inactive_dir) if inactive_exists else 0.0,
            "server_running": server_running,
            "disk_total_mb": disk_total_mb,
            "disk_used_mb": disk_used_mb,
            "disk_free_mb": disk_free_mb,
        }
    )


@worlds_bp.route("/switch", methods=["POST"])
@jwt_required()
def switch_worlds():
    active_dir = current_app.config["WORLD_ACTIVE_DIR"]
    inactive_dir = current_app.config["WORLD_INACTIVE_DIR"]

    # --- Refuse if the server is running ---
    try:
        if _systemctl_is_active() == "active":
            return (
                jsonify(
                    {
                        "error": "Server must be stopped before swapping worlds",
                        "server_running": True,
                    }
                ),
                409,
            )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Failed to check server status (timeout)"}), 504
    except Exception as exc:
        return jsonify({"error": f"Failed to check server status: {exc}"}), 500

    # --- At least one world must exist to swap ---
    active_exists = os.path.isdir(active_dir)
    inactive_exists = os.path.isdir(inactive_dir)

    if not active_exists and not inactive_exists:
        return jsonify({"error": "Neither world folder exists — nothing to swap"}), 400

    temp_dir = os.path.join(os.path.dirname(active_dir), "world_swap_tmp")

    try:
        # --- 3-step atomic rename ---

        # Step 1: active → temp
        if active_exists:
            os.rename(active_dir, temp_dir)

        # Step 2: inactive → active
        if inactive_exists:
            os.rename(inactive_dir, active_dir)

        # Step 3: temp → inactive
        if active_exists:
            os.rename(temp_dir, inactive_dir)

        return jsonify(
            {
                "ok": True,
                "previous_active": _dirname(active_dir)
                if active_exists
                else "(none)",
            }
        )

    except OSError as exc:
        # Attempt to recover: move things back if possible
        try:
            if os.path.isdir(temp_dir):
                os.rename(temp_dir, active_dir)
        except OSError:
            pass
        return jsonify({"error": f"Swap failed: {exc}"}), 500


@worlds_bp.route("/download/<which>", methods=["GET"])
@jwt_required(locations=["headers", "query_string"])
def download_world(which):
    """Download a world folder as a zip.  Accepts JWT via header or ?jwt= query param."""
    if which not in ("active", "inactive"):
        return jsonify({"error": "Invalid value — use 'active' or 'inactive'"}), 400

    target_dir = current_app.config[
        "WORLD_ACTIVE_DIR" if which == "active" else "WORLD_INACTIVE_DIR"
    ]

    if not os.path.isdir(target_dir):
        return jsonify({"error": f"{which.capitalize()} world folder does not exist"}), 404

    try:
        _cleanup_stale_world_tmpdirs()

        # Create the archive in a temp directory that survives until the
        # response is fully sent, then clean it up on close.
        tmpdir_path = tempfile.mkdtemp(prefix=WORLD_TMP_PREFIX)
        zip_basename = f"{which}_world_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        zip_path = os.path.join(tmpdir_path, f"{zip_basename}.zip")
        _create_world_zip(target_dir, zip_path)

        response = send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{zip_basename}.zip",
        )
        response.call_on_close(lambda: shutil.rmtree(tmpdir_path, ignore_errors=True))
        return response
    except Exception as exc:
        import logging
        logging.exception("World download failed")
        return jsonify({"error": f"Failed to create zip: {exc}"}), 500


@worlds_bp.route("/contents/<which>", methods=["GET"])
@jwt_required()
def get_contents(which):
    """Return the list of files and folders in a world directory."""
    if which not in ("active", "inactive"):
        return jsonify({"error": "Invalid value — use 'active' or 'inactive'"}), 400

    target_dir = current_app.config[
        "WORLD_ACTIVE_DIR" if which == "active" else "WORLD_INACTIVE_DIR"
    ]

    if not os.path.isdir(target_dir):
        return jsonify({"error": f"{which.capitalize()} world folder does not exist"}), 404

    return jsonify({"entries": _list_contents(target_dir)})


@worlds_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_world():
    """Accept a zip file and extract it as the inactive world.

    The ZIP is first extracted into a temporary staging directory. We then
    locate the world root by finding a directory that contains ``level.dat``.
    The *contents* of that world root are moved into the inactive world
    directory as its top-level files/folders.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".zip"):
        return jsonify({"error": "Only .zip files are permitted"}), 400

    # Verify ZIP magic number
    magic = file.read(4)
    file.seek(0)
    if magic != b"PK\x03\x04":
        return jsonify({"error": "File does not appear to be a valid ZIP (bad magic bytes)"}), 400

    # Enforce upload size limit
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    max_bytes = current_app.config["MAX_UPLOAD_BYTES"]
    if size > max_bytes:
        return jsonify({"error": f"File exceeds {max_bytes // (1024 * 1024)} MB limit"}), 413

    inactive_dir = current_app.config["WORLD_INACTIVE_DIR"]
    staging_dir = tempfile.mkdtemp(prefix="mcwebadmin_world_upload_")

    try:
        with zipfile.ZipFile(file) as zf:
            for member in zf.infolist():
                member_path = os.path.normpath(member.filename).replace("\\", "/")
                if member_path.startswith("/") or member_path.startswith("../") or "/../" in member_path:
                    return jsonify({"error": f"Unsafe path in zip: {member.filename!r}"}), 400

            zf.extractall(staging_dir)

        world_root = _find_world_root(staging_dir)
        if world_root is None:
            return jsonify({"error": "Could not locate world root (missing or ambiguous level.dat)"}), 400

        # Clean inactive world first so files are never merged.
        _clear_directory_contents(inactive_dir)

        for entry_name in os.listdir(world_root):
            src = os.path.join(world_root, entry_name)
            dst = os.path.join(inactive_dir, entry_name)
            shutil.move(src, dst)

        _ensure_group_writable_tree(inactive_dir)

        return jsonify({"ok": True, "filename": filename})

    except zipfile.BadZipFile as exc:
        return jsonify({"error": f"Bad ZIP file: {exc}"}), 400
    except OSError as exc:
        return jsonify({"error": f"Upload failed: {exc}"}), 500
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
