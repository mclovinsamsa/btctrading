# Guide - Déployer sur RunPod via l'interface web

## 📝 Prérequis

✅ Compte RunPod créé: https://www.runpod.io
✅ Image Docker poussée sur Docker Hub
✅ Crédits RunPod (ou carte bancaire ajoutée)

---

## 🎯 Étape 1: Préparer votre image Docker

### 1.1 Vérifier que l'image est poussée

```bash
# Si pas encore fait:
docker build -t btc-xgb-poc:latest .
docker tag btc-xgb-poc:latest VOTRE_USERNAME/btc-xgb-poc:latest
docker push VOTRE_USERNAME/btc-xgb-poc:latest
```

**Vérifier sur**: https://hub.docker.com/r/VOTRE_USERNAME/btc-xgb-poc

### 1.2 Note l'URI complète de ton image
```
VOTRE_USERNAME/btc-xgb-poc:latest
```

---

## 🚀 Étape 2: Accéder à RunPod Console

1. **Aller sur**: https://www.runpod.io/console/pods

2. **Tu devrais voir**:
   ```
   [Pods] [My Account] [Billing]
   
   Deploy a Pod
   ```

---

## 🔧 Étape 3: Créer un nouveau Pod

### Option A: Via "Any Template" (Recommandé - Plus flexible)

1. **Cliquer sur "Deploy" (bouton bleu)**
2. **Sélectionner "Any Template"**
3. **Remplir les champs**:

#### À4 - Configuration de Base

| Champ | Valeur |
|-------|--------|
| **Container Image** | `VOTRE_USERNAME/btc-xgb-poc:latest` |
| **Container Disk** | `20` GB |
| **Volume** | `10` GB (optionnel, pour persister les données) |

#### À5 - GPU (Optionnel)

| Opション | Valeur |
|----------|--------|
| **GPU Count** | `1` |
| **GPU Type** | Sélectionner dans la liste (RTX 4090, A40, RTX A6000, etc.) |

*Laisser vide pour CPU uniquement*

#### À6 - Ports à Exposer

1. **Cliquer "Add Port"**
2. **Ajouter ces ports**:

   | Port Conteneur | Description | Type |
   |---|---|---|
   | `8888` | Jupyter Lab | HTTP |
   | `5000` | API (optionnel) | HTTP |

3. **Pour chaque port**: Cliquer "Generate"

#### À7 - Configuration Avancée (Optionnel)

Laisser par défaut, sauf si vous avez des besoins spécifiques.

---

## ✅ Étape 4: Vérifier la Configuration

**Avant de déployer**, vérifier:

```
✓ Container Image: VOTRE_USERNAME/btc-xgb-poc:latest
✓ Container Disk: 20GB
✓ GPU: 1 × RTX_4090 (ou CPU)
✓ Ports: 8888, 5000 configurés
```

Si tout est bon → **Cliquer "Deploy"**

---

## ⏳ Étape 5: Attendre le Démarrage

Le pod devrait démarrer en **2-5 minutes**

**Status affiché**:
- 🟡 `PROVISIONING` - En attente
- 🟡 `LAUNCHING` - Démarrage
- 🟢 `RUNNING` - Prêt!

---

## 🌐 Étape 6: Accéder à Jupyter

Une fois le pod en `RUNNING`:

1. **Dans RunPod Console**, cliquer sur le pod
2. **Chercher "Connect"**
3. **Copier l'URL Jupyter** (format: `https://xxx-xxxxx.pod.runpod.io:8888`)
4. **Ouvrir dans le navigateur**

Vous êtes connecté à Jupyter Lab! 🎉

---

## 🖼️ Interface RunPod - Screenshot de référence

```
┌─────────────────────────────────────────────────────────────┐
│ RunPod Console                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Deploy] [My Account] [Billing]                           │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ My Pod: btc-xgb-poc                       STATUS: RUNNING│ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ ID: pod_xxxxx                                           │ │
│ │ Image: user/btc-xgb-poc:latest                         │ │
│ │ GPU: 1 × RTX 4090                                       │ │
│ │ Cost: $0.24/hour                                        │ │
│ │                                                         │ │
│ │ [Connect] [Logs] [Stop] [Delete]                       │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ Ports:                                                 │ │
│ │ • 8888 → https://xxx-xxxxx.runpod.io:8888 [Jupyter]   │ │
│ │ • 5000 → https://xxx-xxxxx.runpod.io:5000 [API]       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Checklist de Déploiement

- [ ] Docker Hub login: `docker login`
- [ ] Image buildée: `docker build -t ...`
- [ ] Image taggée: `docker tag ... yourusername/...`
- [ ] Image poussée: `docker push yourusername/...`
- [ ] Compte RunPod créé
- [ ] Payement validé (carte ou crédits)
- [ ] Image URI vérifiée sur Docker Hub
- [ ] Déploiement sur RunPod lancé
- [ ] Pod atteint `RUNNING`
- [ ] Jupyter accessible via URL

---

## 🐛 Troubleshooting

### Le pod reste en "PROVISIONING"

❌ Trop peu de crédits → Ajouter une carte bancaire
❌ GPU indisponible → Sélectionner une autre GPU
❌ Erreur région → Essayer une autre région

### Erreur: "Image not found"

❌ L'image n'est pas publique sur Docker Hub
✅ Solution:
```bash
# Rendre l'image publique:
# Sur Docker Hub → Repository → Settings → Public

# Ou re-push:
docker push yourusername/btc-xgb-poc:latest
```

### Jupyter ne démarre pas

❌ Port 8888 pas correctement configuré
✅ Vérifier dans la config des ports

### Les données disparaissent entre pods

❌ Volume pas configuré
✅ Lors du déploiement: ajouter "Volume" pour persister

---

## 💰 Coûts

| GPU | Coût/h | Pour | Notes |
|-----|---------|------|-------|
| CPU | $0.02 | Inférence légère | Gratuit ~1h |
| RTX 4090 | $0.24 | ML Training | Bon rapport |
| A40 | $0.40 | Modèles gros | Plus vRAM |
| H100 | $1.50+ | Enterprise | Très cher |

**Astuce**: Terminez les pods quand fini pour ne pas être facturé!

---

## 🎓 Après Déploiement

### Utiliser Jupyter directement

```
https://xxx-xxxxx.runpod.io:8888
```

Tous vos scripts Python sont dans `/app` 🎯

### Exécuter vos scripts depuis Jupyter

```python
# Dans une cellule Jupyter:
import subprocess

# Lancer une entraînement
result = subprocess.run(
    ["python", "/app/src/train_xgb.py"],
    capture_output=True,
    text=True
)
print(result.stdout)
```

### SSH (Optionnel)

RunPod propose aussi SSH:
```bash
ssh -p PORT root@IP
```

---

## 📚 Ressources

- RunPod Docs: https://docs.runpod.io/
- Console: https://www.runpod.io/console/pods
- API Keys: https://www.runpod.io/console/api-keys
- Support: https://runpod.io/console/support

---

## ✨ Tips Avancés

### Sauvegarder l'état du pod

1. **Avant de terminer**: 
   - RunPod Console → Pod → "Save as Template"
   - Cela sauvegarde l'image exacte avec toutes les modifications

2. **Relancer plus tard**:
   - Utiliser le template sauvegardé
   - Récupérer exactement le même état

### Monitorer les coûts en temps réel

RunPod Console → Pod → "Cost per hour"

### Accès SSH sécurisé

```bash
# Sur RunPod Console: [Connect] → SSH
ssh -i ~/.ssh/id_rsa root@<ip> -p <port>
```

### Passer des fichiers

```bash
# Upload depuis votre machine
scp -P <port> fichier.csv root@<ip>:/app/data/

# Download résultats
scp -P <port> root@<ip>:/app/data/results.csv .
```
