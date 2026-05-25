import os
import shutil

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

mods_bp = Blueprint("mods", __name__, url_prefix="/api/mods")

# ------------------------------------------------------------------ #
# Path helpers                                                         #
# ------------------------------------------------------------------ #

def _safe_path(base_dir: str, filename: str) -> str:
    """
    Resolve *filename* relative to *base_dir* and assert the result stays
    within that directory.  Only .jar files are permitted.

    Raises ValueError on any violation (traversal, bad extension).
    """
    # Strip every directory component the caller might have injected
    name = os.path.basename(filename)

    if not name.endswith(".jar"):
        raise ValueError("Only .jar files are permitted")

    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, name))

    # Ensure the resolved path is strictly inside base_dir
    if not target.startswith(base + os.sep):
        raise ValueError("Path traversal detected")

    return target


def _list_mods(directory: str) -> list:
    """Return a sorted list of .jar metadata dicts from *directory*."""
    try:
        entries = []
        for name in os.listdir(directory):
            if name.endswith(".jar"):
                full = os.path.join(directory, name)
                stat = os.stat(full)
                entries.append(
                    {
                        "name": name,
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime),
                    }
                )
        return sorted(entries, key=lambda x: x["name"].lower())
    except FileNotFoundError:
        return []


# ------------------------------------------------------------------ #
# Endpoints                                                            #
# ------------------------------------------------------------------ #

@mods_bp.route("/installed", methods=["GET"])
@jwt_required()
def get_installed():
    return jsonify(_list_mods(current_app.config["MODS_DIR"]))


@mods_bp.route("/stash", methods=["GET"])
@jwt_required()
def get_stash():
    return jsonify(_list_mods(current_app.config["MOD_STASH_DIR"]))


@mods_bp.route("/move_to_stash", methods=["POST"])
@jwt_required()
def move_to_stash():
    data = request.get_json(silent=True)
    if not data or "filename" not in data:
        return jsonify({"error": "filename required"}), 400
    try:
        src = _safe_path(current_app.config["MODS_DIR"], data["filename"])
        dst = _safe_path(current_app.config["MOD_STASH_DIR"], data["filename"])
        if not os.path.isfile(src):
            return jsonify({"error": "File not found"}), 404
        os.rename(src, dst)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Move failed: {exc}"}), 500


@mods_bp.route("/move_to_installed", methods=["POST"])
@jwt_required()
def move_to_installed():
    data = request.get_json(silent=True)
    if not data or "filename" not in data:
        return jsonify({"error": "filename required"}), 400
    try:
        src = _safe_path(current_app.config["MOD_STASH_DIR"], data["filename"])
        dst = _safe_path(current_app.config["MODS_DIR"], data["filename"])
        if not os.path.isfile(src):
            return jsonify({"error": "File not found"}), 404
        os.rename(src, dst)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Move failed: {exc}"}), 500


@mods_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_mod():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    if not filename.endswith(".jar"):
        return jsonify({"error": "Only .jar files are permitted"}), 400

    # Verify JAR magic number (ZIP format: PK\x03\x04)
    magic = file.read(4)
    file.seek(0)
    if magic != b"PK\x03\x04":
        return jsonify({"error": "File does not appear to be a valid JAR (bad magic bytes)"}), 400

    # Enforce upload size limit
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    max_bytes = current_app.config["MAX_UPLOAD_BYTES"]
    if size > max_bytes:
        return jsonify({"error": f"File exceeds {max_bytes // (1024 * 1024)} MB limit"}), 413

    try:
        dst = _safe_path(current_app.config["MOD_STASH_DIR"], filename)
        file.save(dst)
        return jsonify({"ok": True, "filename": filename})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Upload failed: {exc}"}), 500


@mods_bp.route("/stash/<path:filename>", methods=["DELETE"])
@jwt_required()
def delete_from_stash(filename):
    try:
        target = _safe_path(current_app.config["MOD_STASH_DIR"], filename)
        if not os.path.isfile(target):
            return jsonify({"error": "File not found"}), 404
        os.remove(target)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        return jsonify({"error": f"Delete failed: {exc}"}), 500
