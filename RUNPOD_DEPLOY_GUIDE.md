# Déploiement sur RunPod - Guide & Templates

## 📋 Étape 1: Préparer l'image Docker

### 1.1 Créer un compte Docker Hub (ou autre registry)
```bash
# Si vous n'avez pas de compte: https://hub.docker.com
docker login
```

### 1.2 Pousser votre image
```bash
# Taguer avec votre username
docker tag btc-xgb-poc:latest yourusername/btc-xgb-poc:latest

# Pousser sur Docker Hub
docker push yourusername/btc-xgb-poc:latest

# Ou sur GitHub Container Registry (GHCR)
docker tag btc-xgb-poc:latest ghcr.io/yourusername/btc-xgb-poc:latest
docker push ghcr.io/yourusername/btc-xgb-poc:latest
```

## 🚀 Étape 2: Déployer sur RunPod

### Option A: Via l'interface web RunPod (plus simple)

1. **Aller sur https://www.runpod.io/console/pods**

2. **Cliquer "Deploy" → "Any Template"**

3. **Configuration:**
   - **Container Image:** `yourusername/btc-xgb-poc:latest`
   - **Container Disk:** 20GB (minimum)
   - **Volume:** 10GB+ pour vos données (optionnel)
   - **GPU:** Laisser vide pour CPU, ou sélectionner RTX 4090, A40, etc.

4. **Ports à exposer:**
   - `8888` - Jupyter Lab
   - `5000` - API (optionnel)

5. **Environment Variables:**
   ```
   JUPYTER_ENABLE_LAB=yes
   ```

6. **Cliquer "Deploy"** et attendre ~5-10 minutes

---

## 💾 Étape 3: Sauvegarder un Template PersonalisÉ

### Via RunPod API (le plus efficace)

Créez ce fichier pour sauvegarder votre configuration:

```bash
# Fichier: runpod_template.sh
#!/bin/bash

# VOTRE CONFIGURATION RUNPOD
TEMPLATE_NAME="BTC-XGB-POC-GPU"
CONTAINER_IMAGE="yourusername/btc-xgb-poc:latest"
CONTAINER_DISK="20"  # GB
GPU_COUNT="1"
GPU_TYPE="RTX_4090"  # Options: RTX_4090, A40, RTX_A6000, A100, etc.
VOLUME_SIZE="10"     # GB
VOLUME_MOUNT_PATH="/app/data"
PORT_8888="true"     # Jupyter
PORT_5000="false"    # API

# Sauvegarde la config en JSON
cat > runpod_pod_config.json <<EOF
{
  "podName": "${TEMPLATE_NAME}",
  "imageName": "${CONTAINER_IMAGE}",
  "gpuCount": ${GPU_COUNT},
  "gpuType": "${GPU_TYPE}",
  "containerDiskInGb": ${CONTAINER_DISK},
  "volumeInGb": ${VOLUME_SIZE},
  "volumeMountPath": "${VOLUME_MOUNT_PATH}",
  "ports": [
    {
      "containerPort": 8888,
      "description": "Jupyter Lab"
    },
    {
      "containerPort": 5000,
      "description": "API"
    }
  ],
  "env": [
    {
      "key": "JUPYTER_ENABLE_LAB",
      "value": "yes"
    }
  ]
}
EOF

echo "✅ Configuration sauvegardée dans runpod_pod_config.json"
```

---

## 🔄 Étape 4: Relancer rapidement vos Pods

### Script Python pour l'API RunPod

Créez `runpod_deploy.py`:

```python
#!/usr/bin/env python3
import requests
import json
import time
from typing import Dict, Optional

class RunPodDeployer:
    def __init__(self, api_key: str):
        """
        Initialize RunPod API client
        
        Args:
            api_key: Your RunPod API key from https://www.runpod.io/console/api-keys
        """
        self.api_key = api_key
        self.base_url = "https://api.runpod.io/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "RunPod-Deployer/1.0"
        }

    def create_pod(self, config: Dict) -> Optional[str]:
        """
        Create a new pod on RunPod
        
        Args:
            config: Pod configuration dictionary
            
        Returns:
            Pod ID if successful, None otherwise
        """
        query = """
        mutation($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) {
            pod {
              id
              name
              status
            }
            error
          }
        }
        """
        
        variables = {
            "input": {
                "cloudType": "on-demand",
                "gpuCount": config.get("gpu_count", 1),
                "gpuType": config.get("gpu_type", "RTX_4090"),
                "containerDiskInGb": config.get("container_disk", 20),
                "volumeInGb": config.get("volume_size", 10),
                "minVolumeInGb": config.get("volume_size", 10),
                "containerImage": config.get("image"),
                "name": config.get("pod_name"),
                "ports": json.dumps([
                    {"containerPort": 8888, "description": "Jupyter"},
                    {"containerPort": 5000, "description": "API"}
                ]),
                "env": [
                    {"key": "JUPYTER_ENABLE_LAB", "value": "yes"}
                ]
            }
        }
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers={**self.headers, "api_key": self.api_key},
                json=payload
            )
            data = response.json()
            
            if "errors" in data:
                print(f"❌ Error: {data['errors']}")
                return None
                
            pod_id = data.get("data", {}).get("podFindAndDeployOnDemand", {}).get("pod", {}).get("id")
            if pod_id:
                print(f"✅ Pod created: {pod_id}")
                return pod_id
            else:
                print(f"❌ Failed to create pod: {data}")
                return None
                
        except Exception as e:
            print(f"❌ API Error: {e}")
            return None

    def terminate_pod(self, pod_id: str) -> bool:
        """Terminate a pod"""
        query = """
        mutation($input: PodTerminateInput!) {
          podTerminate(input: $input) {
            success
          }
        }
        """
        
        variables = {"input": {"podId": pod_id}}
        payload = {"query": query, "variables": variables}
        
        try:
            response = requests.post(
                self.base_url,
                headers={**self.headers, "api_key": self.api_key},
                json=payload
            )
            data = response.json()
            success = data.get("data", {}).get("podTerminate", {}).get("success", False)
            
            if success:
                print(f"✅ Pod {pod_id} terminated")
            return success
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def get_pod_status(self, pod_id: str) -> Optional[Dict]:
        """Get pod status"""
        query = """
        query($input: PodInput!) {
          pod(input: $input) {
            id
            name
            status
            gpuCount
            gpuType
            runtime {
              gpuCount
              gpuIds
            }
            machine {
              gpuType
            }
          }
        }
        """
        
        variables = {"input": {"podId": pod_id}}
        payload = {"query": query, "variables": variables}
        
        try:
            response = requests.post(
                self.base_url,
                headers={**self.headers, "api_key": self.api_key},
                json=payload
            )
            data = response.json()
            return data.get("data", {}).get("pod")
        except Exception as e:
            print(f"❌ Error: {e}")
            return None


# Exemple d'utilisation
if __name__ == "__main__":
    import os
    import sys
    
    # Remplacer avec votre clé API
    API_KEY = os.getenv("RUNPOD_API_KEY", "your_api_key_here")
    
    deployer = RunPodDeployer(API_KEY)
    
    # Configuration du pod
    pod_config = {
        "pod_name": "BTC-XGB-POC-GPU",
        "image": "yourusername/btc-xgb-poc:latest",
        "gpu_count": 1,
        "gpu_type": "RTX_4090",
        "container_disk": 20,
        "volume_size": 10,
    }
    
    # Créer un pod
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        pod_id = deployer.create_pod(pod_config)
        if pod_id:
            # Attendre que le pod soit prêt
            for i in range(30):
                status = deployer.get_pod_status(pod_id)
                print(f"Status: {status}")
                if status and status.get("status") == "RUNNING":
                    print(f"✅ Pod is ready!")
                    break
                time.sleep(5)
    
    # Terminer un pod
    elif len(sys.argv) > 1 and sys.argv[1] == "terminate":
        deployer.terminate_pod(sys.argv[2])
    
    # Vérifier le statut
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        status = deployer.get_pod_status(sys.argv[2])
        print(json.dumps(status, indent=2))
```

---

## 🎯 Utilisation Rapide

### 1️⃣ Configuration initiale
```bash
# Définir votre clé API RunPod
export RUNPOD_API_KEY="your_runpod_api_key"

# Pousser votre image
docker push yourusername/btc-xgb-poc:latest
```

### 2️⃣ Créer un pod
```bash
python runpod_deploy.py create
```

### 3️⃣ Vérifier le statut
```bash
python runpod_deploy.py status POD_ID_HERE
```

### 4️⃣ Accéder à Jupyter
Allez sur: `https://your-runpod-url:8888`

### 5️⃣ Terminer le pod (quand fini)
```bash
python runpod_deploy.py terminate POD_ID_HERE
```

---

## 📊 Coûts & Configuration GPU

| GPU | Coût/heure | VRAM | Idéal pour |
|-----|-----------|------|-----------|
| RTX 4090 | ~$0.24 | 24GB | Training XGBoost + PyTorch |
| RTX A40 | ~$0.40 | 48GB | Large models |
| A100 | ~$1.00+ | 40-80GB | Enterprise |
| CPU only | ~$0.02 | - | Inférence légère |

---

## 🔐 Variables d'Environnement (Optionnel)

Ajoutez dans votre `.env`:
```
RUNPOD_API_KEY=your_api_key
DOCKER_USERNAME=yourusername
DOCKER_PASSWORD=your_password
CONTAINER_IMAGE=yourusername/btc-xgb-poc:latest
```

---

## 💡 Tips & Tricks

### Persister les données entre pods
```bash
# Monter un volume externe
# Dans RunPod: Volume → /app/data (pour garder vos résultats)
```

### Snapshot un pod (pour sauvegarder l'état)
- RunPod Console → Pod → "Save as Template"
- Permet de relancer avec exactement le même état

### Connecter via SSH
RunPod génère une URL SSH:
```bash
ssh -p <PORT> root@<IP>
```

### Utiliser GPU spécifique
```python
# Pour toujours avoir la même GPU:
gpu_type = "RTX_4090"  # ou "A100", "H100", etc.
```

---

## ⚠️ Troubleshooting

### Le pod ne démarre pas
- Vérifier les logs: `docker logs <container>`
- Vérifier que l'image est accessible publiquement

### Jupyter pas accessible
- Vérifier le port 8888 est exposé
- Utiliser l'URL fournie par RunPod

### Lenteur
- Vérifier la GPU disponible: `nvidia-smi`
- Augmenter la VRAM du conteneur

---

## 📚 Ressources

- RunPod API Docs: https://docs.runpod.io/api/
- Docs: https://docs.runpod.io/
- Support: https://runpod.io/console/support
