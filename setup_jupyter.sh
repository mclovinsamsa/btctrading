#!/bin/bash
# Create Jupyter config directory
mkdir -p /root/.jupyter

# Create Jupyter Lab config file
cat > /root/.jupyter/jupyter_lab_config.py << 'EOF'
# Jupyter Lab Configuration

# Désactiver XSRF protection (problème avec proxy RunPod)
c.ServerApp.disable_check_xsrf = True

# Configurer CORS pour RunPod
c.ServerApp.allow_remote_access = True
c.ServerApp.allow_origin = "*"

# Terminals
c.ServerApp.terminals_enabled = True

# Token et authentification
c.ServerApp.token = ""
c.ServerApp.password = ""
c.ServerApp.allow_root = True

# WebSocket
c.ServerApp.allow_hashed_passwords = False

# IP binding
c.ServerApp.ip = "0.0.0.0"
c.ServerApp.port = 8888

# No browser
c.ServerApp.open_browser = False

# Additional security settings
c.NotebookApp.notebook_dir = "/app"

# Extensions
c.LabApp.dev_mode = False
EOF

echo "Jupyter config created"
