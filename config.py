import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Required secrets (raise KeyError on startup if missing) ---
    JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    ADMIN_PASSWORD_HASH = os.environ["ADMIN_PASSWORD_HASH"]
    RCON_PASSWORD = os.environ["RCON_PASSWORD"]

    # --- RCON ---
    RCON_HOST = os.getenv("RCON_HOST", "127.0.0.1")
    RCON_PORT = int(os.getenv("RCON_PORT", "25575"))

    # --- Paths ---
    MODS_DIR = os.getenv("MODS_DIR", "/opt/fabric/mods")
    MOD_STASH_DIR = os.getenv("MOD_STASH_DIR", "/opt/fabric/mod_stash")
    LOG_PATH = os.getenv("LOG_PATH", "/opt/fabric/logs/latest.log")
    WORLD_ACTIVE_DIR = os.getenv("WORLD_ACTIVE_DIR", "/opt/fabric/world")
    WORLD_INACTIVE_DIR = os.getenv("WORLD_INACTIVE_DIR", "/opt/fabric/world.inactive")

    # --- Service ---
    SERVICE_NAME = os.getenv("SERVICE_NAME", "minecraft-fabric.service")

    # --- Upload limit ---
    MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "150")) * 1024 * 1024

    # --- Flask / JWT ---
    JSON_SORT_KEYS = False
