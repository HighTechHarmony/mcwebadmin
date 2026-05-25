#!/usr/bin/env bash
# =============================================================================
# mcwebadmin system setup — run once as root
# Creates the mcwebadmin user, sets directory permissions, and writes the
# sudoers entry that allows Flask to control minecraft-fabric.service.
# =============================================================================
set -euo pipefail

# ---- constants ---------------------------------------------------------------
MINECRAFT_USER="minecraft"
WEBADMIN_USER="mcwebadmin"
GROUP="mcwebfiles"
FABRIC_DIR="/opt/fabric"
APP_DIR="/home/minecraft/mcwebadmin"
SUDOERS_FILE="/etc/sudoers.d/mcwebadmin"
SYSTEMCTL="/usr/bin/systemctl"
# ------------------------------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: This script must be run as root (sudo $0)" >&2
  exit 1
fi

echo "=== mcwebadmin System Setup ==="
echo

# 1. Verify /opt/fabric exists before we start
if [[ ! -d "$FABRIC_DIR" ]]; then
  echo "ERROR: $FABRIC_DIR does not exist." >&2
  echo "Move (or symlink) your server there first, then re-run this script:" >&2
  echo "  sudo mv /home/minecraft/fabric /opt/fabric" >&2
  echo "  sudo ln -s /opt/fabric /home/minecraft/fabric" >&2
  exit 1
fi

# 2. Create mcwebadmin system user
if id "$WEBADMIN_USER" &>/dev/null; then
  echo "[skip] User '$WEBADMIN_USER' already exists"
else
  echo "[+] Creating system user: $WEBADMIN_USER"
  useradd --system --no-create-home --shell /sbin/nologin "$WEBADMIN_USER"
fi

# 3. Create shared group
if getent group "$GROUP" &>/dev/null; then
  echo "[skip] Group '$GROUP' already exists"
else
  echo "[+] Creating group: $GROUP"
  groupadd "$GROUP"
fi

# 4. Add both users to the shared group
echo "[+] Adding $MINECRAFT_USER and $WEBADMIN_USER to group $GROUP"
usermod -aG "$GROUP" "$MINECRAFT_USER"
usermod -aG "$GROUP" "$WEBADMIN_USER"

# 5. Mods directory — group read/write + setgid
echo "[+] Setting permissions on $FABRIC_DIR/mods"
chown "$MINECRAFT_USER:$GROUP" "$FABRIC_DIR/mods"
chmod 2775 "$FABRIC_DIR/mods"

# 6. Mod stash directory
MOD_STASH="$FABRIC_DIR/mod_stash"
if [[ ! -d "$MOD_STASH" ]]; then
  echo "[+] Creating mod_stash directory"
  mkdir -p "$MOD_STASH"
fi
chown "$MINECRAFT_USER:$GROUP" "$MOD_STASH"
chmod 2775 "$MOD_STASH"

# 7. Logs — group read only
echo "[+] Setting permissions on $FABRIC_DIR/logs"
chown -R "$MINECRAFT_USER:$GROUP" "$FABRIC_DIR/logs"
chmod -R g+rX "$FABRIC_DIR/logs"

# 8. App directory ownership
if [[ -d "$APP_DIR" ]]; then
  echo "[+] Setting ownership of $APP_DIR"
  chown -R "$WEBADMIN_USER:$WEBADMIN_USER" "$APP_DIR"
  # Restrict .env if it exists
  if [[ -f "$APP_DIR/.env" ]]; then
    chmod 600 "$APP_DIR/.env"
  fi
fi

# 9. Sudoers entry
echo "[+] Writing sudoers entry: $SUDOERS_FILE"
cat > "$SUDOERS_FILE" <<EOF
# mcwebadmin — passwordless systemctl access for minecraft-fabric.service only
$WEBADMIN_USER ALL=(ALL) NOPASSWD: $SYSTEMCTL start minecraft-fabric.service
$WEBADMIN_USER ALL=(ALL) NOPASSWD: $SYSTEMCTL stop minecraft-fabric.service
$WEBADMIN_USER ALL=(ALL) NOPASSWD: $SYSTEMCTL restart minecraft-fabric.service
$WEBADMIN_USER ALL=(ALL) NOPASSWD: $SYSTEMCTL is-active minecraft-fabric.service
EOF
chmod 440 "$SUDOERS_FILE"

# Validate before leaving it in place
if visudo -cf "$SUDOERS_FILE"; then
  echo "[+] Sudoers entry validated OK"
else
  echo "ERROR: visudo validation failed — removing bad entry" >&2
  rm -f "$SUDOERS_FILE"
  exit 1
fi

echo
echo "=== Setup complete ==="
echo
echo "Remaining steps (run as the minecraft user unless noted):"
echo
echo "  1. Enable RCON in /opt/fabric/server.properties:"
echo "       enable-rcon=true"
echo "       rcon.port=25575"
echo "       rcon.password=<strong-random-password>"
echo
echo "  2. Create .env:"
echo "       cd $APP_DIR"
echo "       cp .env.example .env"
echo "       chmod 600 .env"
echo
echo "  3. Generate a JWT secret key:"
echo "       python3 -c \"import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))\""
echo "     Add the output line to .env"
echo
echo "  4. Set admin password:"
echo "       python3 scripts/set_password.py"
echo "     Paste the ADMIN_PASSWORD_HASH= line into .env"
echo
echo "  5. Set RCON_PASSWORD in .env to match server.properties"
echo
echo "  6. Install Python dependencies:"
echo "       python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
echo
echo "  7. Build the React frontend:"
echo "       cd frontend && npm install && npm run build"
echo
echo "  8. Install and start the systemd service (as root):"
echo "       sudo cp $APP_DIR/mcwebadmin.service /etc/systemd/system/"
echo "       sudo systemctl daemon-reload"
echo "       sudo systemctl enable --now mcwebadmin"
echo
echo "  9. Verify:"
echo "       sudo systemctl status mcwebadmin"
echo "       curl http://localhost:8080/api/auth/verify"
