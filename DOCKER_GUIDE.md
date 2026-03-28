# Guide Docker - BTC XGB POC

## 📋 Prérequis
- Docker installé sur votre machine
- Au moins 10GB d'espace disque libre

## 🔨 Construction de l'image

### Option 1: Image CPU (recommandée pour la plupart)
```bash
docker build -t btc-xgb-poc:latest .
```

### Option 2: Image GPU (si vous avez une GPU NVIDIA avec CUDA)
Modifiez la ligne PyTorch dans le Dockerfile:
```dockerfile
RUN pip install --no-cache-dir torch==2.8.0 torchvision==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu118
```
Puis construisez avec:
```bash
docker build -t btc-xgb-poc:gpu .
```

## 🚀 Lancer le conteneur

### Localement avec Jupyter
```bash
docker run -p 8888:8888 -p 5000:5000 -v ~/btc_xgb_poc:/app btc-xgb-poc:latest
```

Jupyter Lab sera disponible à: `http://localhost:8888`

### Avec volume persistant pour les données
```bash
docker run -p 8888:8888 \
  -v ~/btc_xgb_poc:/app \
  -v ~/btc_data:/app/data \
  btc-xgb-poc:latest
```

### Mode bash interactif
```bash
docker run -it -v ~/btc_xgb_poc:/app btc-xgb-poc:latest bash
```

### Exécuter un script Python
```bash
docker run -v ~/btc_xgb_poc:/app btc-xgb-poc:latest python src/train_xgb.py
```

## ☸️ Sur Kubernetes/Pod

### 1. Pousser l'image sur un registry (Docker Hub, ECR, etc.)
```bash
# Taguer l'image
docker tag btc-xgb-poc:latest your-registry/btc-xgb-poc:latest

# Pousser
docker push your-registry/btc-xgb-poc:latest
```

### 2. Exemple de manifeste Pod Kubernetes
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: btc-xgb-jupyter
spec:
  containers:
  - name: btc-xgb
    image: your-registry/btc-xgb-poc:latest
    ports:
    - containerPort: 8888
      name: jupyter
    - containerPort: 5000
      name: api
    resources:
      requests:
        memory: "4Gi"
        cpu: "2"
      limits:
        memory: "8Gi"
        cpu: "4"
    volumeMounts:
    - name: app-storage
      mountPath: /app
    - name: data-storage
      mountPath: /app/data
    env:
    - name: JUPYTER_ENABLE_LAB
      value: "yes"
  volumes:
  - name: app-storage
    persistentVolumeClaim:
      claimName: app-pvc
  - name: data-storage
    emptyDir: {}
```

### 3. Appliquer sur Kubernetes
```bash
kubectl apply -f pod.yaml

# Accéder à Jupyter via port-forward
kubectl port-forward btc-xgb-jupyter 8888:8888
```

## 📊 Taille de l'image
~3-4GB (dépend de PyTorch et compilation)

Pour réduire la taille, vous pouvez:
- Utiliser `torch` sans `torchvision` et `torchaudio` si inutiles
- Utiliser `python:3.11-alpine` au lieu de `slim` (plus petit mais peut avoir des problèmes de compilation)

## 🔐 Production
Pour la production, ajoutez:
- Un fichier `.env` pour les variables d'environnement
- Une configuration Jupyter sécurisée (token/password)
- Un reverse proxy (nginx/traefik)
- Des limites de ressources

Modifiez la dernière ligne du Dockerfile pour une configuration sécurisée:
```dockerfile
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
```

## 🛠️ Troubleshooting

**L'image est trop grande:**
Réduisez les couches avec des `&&` et nettoyez après chaque installation.

**Problème de GPU:**
Utilisez l'image `nvidia/cuda:12.1-runtime-ubuntu22.04` comme base.

**Jupyter ne démarre pas:**
Vérifiez les logs: `docker logs <container_id>`
