# Utiliser une image Python 3.11 slim
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    bash \
    bash-completion \
    nano \
    ca-certificates \
    nodejs \
    npm \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers requirements
COPY requirements.txt .

# Installer PyTorch 2.8.0 (CPU uniquement)
# Note: torchvision et torchaudio ne sont pas disponibles pour PyTorch 2.8.0 CPU
RUN pip install --no-cache-dir torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu

# Installer les autres dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Upgrades pip et réinstaller jupyterlab complètement
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --force-reinstall jupyterlab

# Copier le script de setup Jupyter
COPY setup_jupyter.sh .
RUN chmod +x setup_jupyter.sh && ./setup_jupyter.sh

# Copier le code source
COPY . .

# Exposer le port Jupyter
EXPOSE 8888

# Exposer le port par défaut si vous avez une API
EXPOSE 5000

# Commande par défaut: lancer Jupyter Lab avec config
CMD ["jupyter", "lab", "--config=/root/.jupyter/jupyter_lab_config.py"]
