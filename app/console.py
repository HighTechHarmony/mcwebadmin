import logging
import sys
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from mcrcon import MCRcon

console_bp = Blueprint("console", __name__, url_prefix="/api/console")

_MAX_CMD_LEN = 1024


def _rcon(command: str) -> str:
    host = current_app.config.get("RCON_HOST", "127.0.0.1")
    port = int(current_app.config.get("RCON_PORT", 25575))
    password = current_app.config.get("RCON_PASSWORD")
    
    try:
        with MCRcon(host, password, port=port) as mcr:
            resp = mcr.command(command)
            return resp
    except Exception as e:
        raise e


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
        if response is None:
            response = "(No response from server)"
        
        # Normalize line endings: remove CR and ensure only LF is used.
        # Minecraft RCON can sometimes return messy strings depending on the command.
        response = str(response).replace("\r\n", "\n").replace("\r", "\n")

        # The `/help` response is often returned as a long single string with
        # commands separated by leading slashes ("/cmd1/cmd2/..."). For
        # readability in the web UI, insert a newline before each leading
        # slash for the help output only. This avoids globally changing
        # separators for other commands.
        try:
            if command.strip().lower() == "help":
                # Insert newline before every '/' so each command begins on
                # its own line, then collapse any accidental double-newlines.
                response = response.replace("/", "\n/")
                # Remove a possible leading newline we just introduced.
                if response.startswith("\n"):
                    response = response[1:]
                # Collapse multiple newlines into single ones.
                while "\n\n" in response:
                    response = response.replace("\n\n", "\n")
        except Exception:
            # If anything goes wrong here, fall back to the original response.
            pass
        
        return jsonify({"response": response})
    except ConnectionRefusedError:
        return jsonify({"error": "RCON unavailable — is the server running?"}), 502
    except Exception as exc:
        return jsonify({"error": f"RCON error: {exc}"}), 502
