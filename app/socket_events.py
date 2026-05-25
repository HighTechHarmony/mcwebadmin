"""
Background log-tail thread and Socket.IO event handlers for /console namespace.

The log-tail thread opens latest.log, seeks to EOF, and streams new lines to
all connected clients via the 'log_line' event.  It detects log rotation by
watching the file inode and reopens the file when Minecraft starts a new
session.
"""

import os
import threading
import time

from flask_jwt_extended import decode_token
from flask_socketio import emit, disconnect


_MAX_CMD_LEN = 1024


def register(socketio, log_path: str) -> None:
    """Register Socket.IO event handlers and start the log-tail thread."""
    _register_events(socketio)
    thread = threading.Thread(
        target=_tail_loop, args=(socketio, log_path), daemon=True, name="log-tail"
    )
    thread.start()


# ------------------------------------------------------------------ #
# Log tail                                                             #
# ------------------------------------------------------------------ #

def _tail_loop(socketio, log_path: str) -> None:
    """Outer loop: restarts _tail_file on any unexpected exception."""
    while True:
        try:
            _tail_file(socketio, log_path)
        except Exception:
            time.sleep(2)


def _tail_file(socketio, log_path: str) -> None:
    """
    Wait for the log file to exist, then tail it.  Returns when the file is
    rotated (inode changes) or disappears, so the caller can reopen it.
    """
    while not os.path.exists(log_path):
        time.sleep(2)

    with open(log_path, "r", errors="replace") as fh:
        current_inode = os.fstat(fh.fileno()).st_ino
        fh.seek(0, 2)  # seek to end — don't replay history

        while True:
            line = fh.readline()
            if line:
                socketio.emit(
                    "log_line",
                    {"data": line.rstrip()},
                    namespace="/console",
                )
            else:
                time.sleep(0.1)
                # Detect log rotation: inode changed or file deleted
                try:
                    if os.stat(log_path).st_ino != current_inode:
                        return  # reopen
                except FileNotFoundError:
                    return  # reopen


# ------------------------------------------------------------------ #
# Socket.IO events                                                     #
# ------------------------------------------------------------------ #

def _register_events(socketio) -> None:

    @socketio.on("connect", namespace="/console")
    def on_connect(auth):
        """Validate JWT on WebSocket connection; reject if invalid."""
        token = (auth or {}).get("token")
        if not token:
            return False  # reject
        try:
            decode_token(token)
        except Exception:
            return False  # reject

    @socketio.on("send_command", namespace="/console")
    def on_send_command(data):
        """
        Accept a command from the client, execute it via RCON, and emit the
        response back to the originating socket.
        """
        from flask import current_app
        from mcrcon import MCRcon

        command = str((data or {}).get("command", "")).strip()
        if not command or len(command) > _MAX_CMD_LEN:
            return

        try:
            host = current_app.config["RCON_HOST"]
            port = current_app.config["RCON_PORT"]
            password = current_app.config["RCON_PASSWORD"]
            with MCRcon(host, password, port=port) as mcr:
                response = mcr.command(command)
            emit("command_response", {"response": response})
        except ConnectionRefusedError:
            emit("command_response", {"error": "RCON unavailable — is the server running?"})
        except Exception as exc:
            emit("command_response", {"error": f"RCON error: {exc}"})
