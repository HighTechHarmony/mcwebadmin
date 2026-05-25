from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from mcrcon import MCRcon

console_bp = Blueprint("console", __name__, url_prefix="/api/console")

_MAX_CMD_LEN = 1024


def _rcon(command: str) -> str:
    host = current_app.config["RCON_HOST"]
    port = current_app.config["RCON_PORT"]
    password = current_app.config["RCON_PASSWORD"]
    with MCRcon(host, password, port=port) as mcr:
        return mcr.command(command)


@console_bp.route("/command", methods=["POST"])
@jwt_required()
def send_command():
    data = request.get_json(silent=True)
    if not data or "command" not in data:
        return jsonify({"error": "command field required"}), 400

    command = str(data["command"]).strip()
    if not command:
        return jsonify({"error": "Command cannot be empty"}), 400
    if len(command) > _MAX_CMD_LEN:
        return jsonify({"error": f"Command exceeds {_MAX_CMD_LEN} character limit"}), 400

    try:
        response = _rcon(command)
        return jsonify({"response": response})
    except ConnectionRefusedError:
        return jsonify({"error": "RCON unavailable — is the server running?"}), 502
    except Exception as exc:
        return jsonify({"error": f"RCON error: {exc}"}), 502
