# 🚀 Quick Start - RunPod Deployment

## ⏱️ 5-Minute Setup

### 1. Configuration initiale (une seule fois)

```bash
# 1.1 Copier le fichier de configuration
cp .env.runpod.example .env.runpod

# 1.2 Éditer avec vos valeurs
# - RUNPOD_API_KEY: aller sur https://www.runpod.io/console/api-keys
# - DOCKER_USERNAME/PASSWORD: aller sur https://hub.docker.com
nano .env.runpod
```

### 2. Pousser votre image Docker

```bash
# Depuis la racine du projet
docker build -t btc-xgb-poc:latest .

# Pousser vers Docker Hub
./runpod_quick_deploy.sh push
```

### 3. Créer votre premier pod

```bash
./runpod_quick_deploy.sh create
```

**Le pod démarre en 2-5 minutes** ✨

### 4. Accéder à Jupyter

L'URL est affichée dans RunPod console:
- Allez sur https://www.runpod.io/console/pods
- Cliquez sur votre pod
- Cliquez sur "Connect" → "Jupyter Lab"

---

## 🔄 Workflows Courants

### Relancer rapidement un pod avec la même config

```bash
# Créer un nouveau pod (avec la config sauvegardée)
./runpod_quick_deploy.sh create

# Voir l'ID du pod
./runpod_quick_deploy.sh list
```

### Sauvegarder votre configuration

```bash
# Sauvegarder une config réutilisable
./runpod_quick_deploy.sh save my-xgb-config

# Plus tard, la réutiliser facilement avec:
# python runpod_deploy.py load my-xgb-config
```

### Terminer un pod quand fini

```bash
./runpod_quick_deploy.sh terminate pod_xxxxx
```

### Vérifier tous vos pods actifs

```bash
./runpod_quick_deploy.sh list
```

---

## 💡 Astuces

| Tâche | Commande |
|------|----------|
| Deploy complet | `./runpod_quick_deploy.sh deploy` |
| Voir la config | `./runpod_quick_deploy.sh config` |
| Checker le statut | `./runpod_quick_deploy.sh status POD_ID` |
| Voir tous les pods | `./runpod_quick_deploy.sh list` |

---

## 📊 Coûts

| GPU | Coût/h | VRAM |
|-----|---------|------|
| RTX 4090 | ~$0.24 | 24GB |
| RTX A40 | ~$0.40 | 48GB |

**Conseil**: Terminez toujours vos pods après utilisation! ⚠️

---

## ❓ FAQ

**Q: Comment modifier la GPU?**
```bash
# Éditer .env.runpod
GPU_TYPE=A100  # au lieu de RTX_4090
```

**Q: Où vont mes données?**
- Jupyter tab: `/app/data`
- Volume externe: sauvegardé automatiquement

**Q: Perte de données entre pods?**
- Volume RunPod: OUI, persistent
- Code: NON, re-pull depuis Docker

**Q: Comment accéder via SSH?**
- RunPod Console → Pod → "Connect" → SSH

**Q: Relancer avec le même environnement?**
```bash
# Sauvegarder un snapshot avant de terminer
# Relancer depuis ce snapshot plus tard
```

---

## 🆘 Troubleshooting

| Problème | Solution |
|----------|----------|
| Pod ne démarre | Vérifier les logs: `docker logs <container>` |
| Jupyter pas accessible | Vérifier port 8888 exposé |
| Erreur API | Vérifier `RUNPOD_API_KEY` dans `.env.runpod` |
| Image trop lente à pull | Utiliser `docker push` depuis RunPod |

---

## 📖 Fichiers clés

- `Dockerfile` - Configuration de l'image
- `.env.runpod` - Configuration RunPod (ne pas commiter!)
- `runpod_deploy.py` - Script Python pour l'API RunPod
- `runpod_quick_deploy.sh` - Bash wrapper (le plus simple)

---

## 🎯 Workflow complet en 3 commandes

```bash
# 1. Setup initial
cp .env.runpod.example .env.runpod
nano .env.runpod  # ajouter vos clés

# 2. Deploy en une commande
./runpod_quick_deploy.sh deploy

# 3. Voir votre pod
./runpod_quick_deploy.sh list
```

Voilà! Votre pod est prêt 🎉
