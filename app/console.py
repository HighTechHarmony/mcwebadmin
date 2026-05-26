import logging
import sys
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from mcrcon import MCRcon
import os

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


def _tail_lines(path: str, max_lines: int = 1000):
    """Return the last `max_lines` lines from the file at `path`.
    This reads from the end of the file in blocks to avoid loading the
    entire file into memory.
    """
    if max_lines <= 0:
        return []

    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            filesize = fh.tell()
            if filesize == 0:
                return []

            block_size = 8192
            data = bytearray()
            pos = filesize

            # Read backwards in blocks until we have enough newlines
            while pos > 0 and data.count(b"\n") <= max_lines:
                read_size = min(block_size, pos)
                pos -= read_size
                fh.seek(pos)
                chunk = fh.read(read_size)
                data[0:0] = chunk  # prepend

                # If we've reached start of file, stop
                if pos == 0:
                    break

            # Split into lines and return the last `max_lines`
            lines = data.splitlines()
            return [ln.decode("utf-8", errors="replace") for ln in lines[-max_lines:]]
    except FileNotFoundError:
        return []
    except Exception:
        logging.exception("Failed to read log file")
        return []


@console_bp.route("/log", methods=["GET"])
@jwt_required()
def get_log():
    """Return the last N lines from the configured log file as JSON.

    Query param: `lines` (optional, default 1000, max 5000)
    """
    try:
        max_lines = int(request.args.get("lines", 1000))
    except Exception:
        max_lines = 1000

    max_lines = max(1, min(max_lines, 5000))
    log_path = current_app.config.get("LOG_PATH", "/opt/fabric/logs/latest.log")

    if not os.path.exists(log_path):
        return jsonify({"lines": []})

    lines = _tail_lines(log_path, max_lines)
    return jsonify({"lines": lines})
