from gevent import monkey

monkey.patch_all()

from app import create_app, socketio  # noqa: E402 — import after monkey-patch

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, debug=False)
