import subprocess

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required

server_bp = Blueprint("server", __name__, url_prefix="/api/server")

_ALLOWED_ACTIONS = {"start", "stop", "restart", "is-active"}


def _systemctl(action: str) -> subprocess.CompletedProcess:
    if action not in _ALLOWED_ACTIONS:
        raise ValueError(f"Disallowed systemctl action: {action!r}")
    service = current_app.config["SERVICE_NAME"]
    return subprocess.run(
        ["sudo", "systemctl", action, service],
        capture_output=True,
        text=True,
        timeout=30,
    )


@server_bp.route("/status", methods=["GET"])
@jwt_required()
def status():
    result = _systemctl("is-active")
    raw = result.stdout.strip() or "inactive"
    return jsonify({"status": raw})


@server_bp.route("/start", methods=["POST"])
@jwt_required()
def start():
    result = _systemctl("start")
    return jsonify({"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()})


@server_bp.route("/stop", methods=["POST"])
@jwt_required()
def stop():
    result = _systemctl("stop")
    return jsonify({"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()})


@server_bp.route("/restart", methods=["POST"])
@jwt_required()
def restart():
    result = _systemctl("restart")
    return jsonify({"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()})
