#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mclovinsamsa/btctrading.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
PROJECT_DIR="${PROJECT_DIR:-$WORKSPACE_DIR/btctrading}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
LEGACY_VENV_DIR="${LEGACY_VENV_DIR:-$PROJECT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"
JUPYTER_TOKEN="${JUPYTER_TOKEN:-}"
INSTALL_SYSTEM_DEPS="${INSTALL_SYSTEM_DEPS:-1}"
SETUP_JUPYTER="${SETUP_JUPYTER:-1}"
PREPARE_DATA="${PREPARE_DATA:-0}"
MODEL_ARCHIVE_URL="${MODEL_ARCHIVE_URL:-}"
DATA_ARCHIVE_URL="${DATA_ARCHIVE_URL:-}"
EXTRA_PIP_PACKAGES="${EXTRA_PIP_PACKAGES:-}"
POST_SETUP_COMMAND="${POST_SETUP_COMMAND:-}"
TORCH_VERSION="${TORCH_VERSION:-2.8.0}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-}"
SKIP_TORCH_INSTALL="${SKIP_TORCH_INSTALL:-0}"
FINAL_VALIDATION_DEVICE="${FINAL_VALIDATION_DEVICE:-cuda}"
FINAL_VALIDATION_HOLDOUT_RATIO="${FINAL_VALIDATION_HOLDOUT_RATIO:-0.2}"
FINAL_VALIDATION_FEE="${FINAL_VALIDATION_FEE:-0.0004}"
FINAL_VALIDATION_SLIPPAGE="${FINAL_VALIDATION_SLIPPAGE:-0.0008}"
FINAL_VALIDATION_WF_WINDOWS="${FINAL_VALIDATION_WF_WINDOWS:-4}"

log() {
    echo "[bootstrap] $*"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Commande requise introuvable: $1" >&2
        exit 1
    }
}

install_system_deps() {
    if [[ "$INSTALL_SYSTEM_DEPS" != "1" ]]; then
        log "Installation système ignorée"
        return
    fi

    if ! command -v apt-get >/dev/null 2>&1; then
        log "apt-get absent, je saute l'installation des paquets système"
        return
    fi

    export DEBIAN_FRONTEND=noninteractive
    log "Installation des dépendances système"
    apt-get update
    apt-get install -y --no-install-recommends \
        bash \
        bash-completion \
        build-essential \
        ca-certificates \
        curl \
        git \
        htop \
        nano \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        tmux \
        unzip \
        wget
    rm -rf /var/lib/apt/lists/*
}

sync_repo() {
    mkdir -p "$WORKSPACE_DIR"

    if [[ -d "$PROJECT_DIR/.git" ]]; then
        log "Mise a jour du repo existant dans $PROJECT_DIR"
        git -C "$PROJECT_DIR" fetch origin
        git -C "$PROJECT_DIR" checkout "$REPO_BRANCH"
        git -C "$PROJECT_DIR" pull --ff-only origin "$REPO_BRANCH"
    else
        log "Clonage du repo dans $PROJECT_DIR"
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR"
    fi
}

setup_venv() {
    require_cmd "$PYTHON_BIN"

    if [[ ! -d "$VENV_DIR" ]]; then
        log "Creation du virtualenv dans $VENV_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi

    if [[ "$LEGACY_VENV_DIR" != "$VENV_DIR" ]]; then
        ln -sfn "$VENV_DIR" "$LEGACY_VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    log "Mise a niveau de pip/setuptools/wheel"
    pip install --upgrade pip setuptools wheel
}

install_python_deps() {
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    local requirements_file="$PROJECT_DIR/requirements.txt"
    local filtered_requirements

    if [[ ! -f "$requirements_file" ]]; then
        echo "requirements.txt introuvable dans $PROJECT_DIR" >&2
        exit 1
    fi

    if [[ "$SKIP_TORCH_INSTALL" != "1" ]]; then
        if [[ -n "$TORCH_INDEX_URL" ]]; then
            log "Installation de torch==$TORCH_VERSION depuis $TORCH_INDEX_URL"
            pip install "torch==$TORCH_VERSION" --index-url "$TORCH_INDEX_URL"
        else
            log "Installation de torch via requirements.txt"
        fi
    else
        log "Installation de torch ignoree"
    fi

    filtered_requirements="$(mktemp)"
    if [[ "$SKIP_TORCH_INSTALL" != "1" && -n "$TORCH_INDEX_URL" ]]; then
        grep -vE '^torch([<>=!~].*)?$' "$requirements_file" > "$filtered_requirements"
    else
        cp "$requirements_file" "$filtered_requirements"
    fi

    log "Installation des dependances Python"
    pip install -r "$filtered_requirements"
    rm -f "$filtered_requirements"

    if [[ -n "$EXTRA_PIP_PACKAGES" ]]; then
        log "Installation des paquets Python additionnels"
        pip install $EXTRA_PIP_PACKAGES
    fi
}

setup_directories() {
    log "Creation de l'arborescence de travail"
    mkdir -p \
        "$PROJECT_DIR/data" \
        "$PROJECT_DIR/models" \
        "$PROJECT_DIR/artifacts" \
        "$PROJECT_DIR/logs" \
        "$PROJECT_DIR/notebooks"
}

download_and_extract() {
    local url="$1"
    local destination="$2"
    local archive

    [[ -z "$url" ]] && return

    mkdir -p "$destination"
    archive="$(mktemp)"

    log "Telechargement de $url"
    curl -L "$url" -o "$archive"

    case "$url" in
        *.tar.gz|*.tgz)
            tar -xzf "$archive" -C "$destination"
            ;;
        *.tar)
            tar -xf "$archive" -C "$destination"
            ;;
        *.zip)
            unzip -o "$archive" -d "$destination"
            ;;
        *)
            local filename
            filename="$(basename "$url")"
            mv "$archive" "$destination/$filename"
            archive=""
            ;;
    esac

    if [[ -n "${archive:-}" && -f "$archive" ]]; then
        rm -f "$archive"
    fi
}

setup_jupyter_config() {
    if [[ "$SETUP_JUPYTER" != "1" ]]; then
        log "Configuration Jupyter ignoree"
        return
    fi

    mkdir -p /root/.jupyter
    cat > /root/.jupyter/jupyter_lab_config.py <<EOF
c.ServerApp.disable_check_xsrf = True
c.ServerApp.allow_remote_access = True
c.ServerApp.allow_origin = "*"
c.ServerApp.terminals_enabled = True
c.ServerApp.token = "${JUPYTER_TOKEN}"
c.ServerApp.password = ""
c.ServerApp.allow_root = True
c.ServerApp.allow_hashed_passwords = False
c.ServerApp.ip = "0.0.0.0"
c.ServerApp.port = ${JUPYTER_PORT}
c.ServerApp.open_browser = False
c.ServerApp.root_dir = "${PROJECT_DIR}"
c.NotebookApp.notebook_dir = "${PROJECT_DIR}"
c.LabApp.dev_mode = False
EOF

    cat > "$PROJECT_DIR/start_jupyter.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${VENV_DIR}/bin/activate"
cd "${PROJECT_DIR}"
exec jupyter lab --config=/root/.jupyter/jupyter_lab_config.py
EOF
    chmod +x "$PROJECT_DIR/start_jupyter.sh"
}

setup_validation_helpers() {
    cat > "$PROJECT_DIR/run_final_validation.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${VENV_DIR}/bin/activate"
cd "${PROJECT_DIR}"
export PYTHONDONTWRITEBYTECODE=1
exec python -m src.research.final_validation \
  --best-config data/funnel_best_config.json \
  --device ${FINAL_VALIDATION_DEVICE} \
  --holdout-ratio ${FINAL_VALIDATION_HOLDOUT_RATIO} \
  --fee ${FINAL_VALIDATION_FEE} \
  --slippage ${FINAL_VALIDATION_SLIPPAGE} \
  --wf-windows ${FINAL_VALIDATION_WF_WINDOWS}
EOF
    chmod +x "$PROJECT_DIR/run_final_validation.sh"
}

prepare_project_data() {
    if [[ "$PREPARE_DATA" != "1" ]]; then
        log "Preparation des donnees ignoree"
        return
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_DIR"

    log "Telechargement de l'historique Binance"
    python src/download_binance.py

    log "Construction des features"
    python src/build_features.py
}

run_post_setup() {
    [[ -z "$POST_SETUP_COMMAND" ]] && return

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_DIR"

    log "Execution de la commande post-setup"
    bash -lc "$POST_SETUP_COMMAND"
}

print_summary() {
    cat <<EOF

Bootstrap termine.

Repo      : $PROJECT_DIR
Venv      : $VENV_DIR
Jupyter   : port $JUPYTER_PORT
Commande  : cd $PROJECT_DIR && ./start_jupyter.sh

Variables utiles:
  REPO_URL=$REPO_URL
  REPO_BRANCH=$REPO_BRANCH
  PREPARE_DATA=$PREPARE_DATA
  MODEL_ARCHIVE_URL=${MODEL_ARCHIVE_URL:-<vide>}
  DATA_ARCHIVE_URL=${DATA_ARCHIVE_URL:-<vide>}
EOF
}

main() {
    install_system_deps
    require_cmd git
    require_cmd curl

    sync_repo
    setup_venv
    install_python_deps
    setup_directories
    download_and_extract "$MODEL_ARCHIVE_URL" "$PROJECT_DIR/models"
    download_and_extract "$DATA_ARCHIVE_URL" "$PROJECT_DIR/data"
    setup_jupyter_config
    setup_validation_helpers
    prepare_project_data
    run_post_setup
    print_summary
}

main "$@"
