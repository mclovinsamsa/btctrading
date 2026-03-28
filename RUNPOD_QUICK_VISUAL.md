# 🎬 RunPod Interface - Guide Visuel Rapide (2 min)

## 📋 Avant de commencer

Avoir prêt:
```
1. Votre image Docker Hub: user/btc-xgb-poc:latest
2. Votre compte RunPod avec crédit
3. Le lien: https://www.runpod.io/console/pods
```

---

## 🚀 Les 7 Étapes (Copy-Paste)

### Étape 1: Ouvrir RunPod Console
```
https://www.runpod.io/console/pods
```

### Étape 2: Cliquer "Deploy"
```
Gros bouton bleu "Deploy" en haut à droite
```

### Étape 3: Sélectionner "Any Template"
```
Écran: "Select a Template"
→ Cliquer "Any Template" (bas de la page)
```

### Étape 4: Remplir l'image Docker

Dans le formulaire qui s'affiche:

```
┌─────────────────────────────────────────┐
│ Container Image *                       │
│ [user/btc-xgb-poc:latest              ] │  ← VOTRE IMAGE ICI
└─────────────────────────────────────────┘
```

### Étape 5: Configuration (scroll down)

| Champ | Valeur |
|-------|--------|
| Container Disk | `20` |
| Volume (optional) | `10` |
| GPU Count | `1` |
| GPU Type | Select: `RTX_4090` |

### Étape 6: Ajouter les ports

```
Scroll → "Add Mapped Ports"

Port 1:
  Container Port: 8888
  [Generate]

Port 2:
  Container Port: 5000
  [Generate]
```

### Étape 7: Déployer

```
Scroll jusqu'à "Deploy" (bleu)
Cliquer!
```

---

## ⏳ Attendre (3-5 minutes)

Vous verrez:
```
🟡 PROVISIONING → 🟡 LAUNCHING → 🟢 RUNNING
```

---

## 💬 Une fois "RUNNING"

### Accéder à Jupyter

1. Dans RunPod Console, cliquer sur votre pod
2. Voir le panel "Port Mappings"
3. Copier le lien pour le port 8888
4. Ouvrir dans le navigateur

**Tout est prêt!** Vous êtes sur Jupyter 🎉

---

## 📱 L'interface pas à pas (Visuelle)

```
ÉTAPE 1-2: Console RunPod
┌────────────────────────────────┐
│ My Pods | [Deploy] ↑           │
├────────────────────────────────┤
│ (aucun pod)                    │
└────────────────────────────────┘

         ↓ Cliquer Deploy → Any Template

ÉTAPE 3: Template Selection
┌────────────────────────────────┐
│ Compute        GPU Providers   │
│ Templates      Community       │
│              [Any Template] ← │
└────────────────────────────────┘

         ↓ Remplir formulaire

ÉTAPE 4-6: Configuration
┌────────────────────────────────┐
│ Container Image:               │
│ [user/btc-xgb-poc:latest    ] │
│                                │
│ Container Disk: [20]           │
│ GPU: [1] RTX_4090              │
│                                │
│ Ports: 8888, 5000             │
│                                │
│ [Cancel] [Deploy] ↑            │
└────────────────────────────────┘

         ↓ Cliquer Deploy

ÉTAPE 7: Pod Démarrage
┌────────────────────────────────┐
│ Pod: btc-xgb-poc               │
│ Status: 🟡 PROVISIONING...     │
│ (attendre...)                  │
└────────────────────────────────┘

         ↓ 2-5 minutes plus tard

ÉTAPE 8: Pod Prêt ✅
┌────────────────────────────────┐
│ Pod: btc-xgb-poc               │
│ Status: 🟢 RUNNING             │
│                                │
│ Port 8888:                     │
│ https://xxx-yyyy.runpod.io:8888│
│ [Open in Browser] ← Cliquer!   │
└────────────────────────────────┘

         ↓ Jupyter Lab s'ouvre

         ✨ C'est prêt!
```

---

## ⚡ Checklist Rapide

- [ ] Image poussée sur Docker Hub
- [ ] Lien: `user/btc-xgb-poc:latest`
- [ ] Compte RunPod avec crédit
- [ ] Deploy → Any Template
- [ ] `user/btc-xgb-poc:latest` dans "Container Image"
- [ ] GPU: `1 × RTX_4090` (ou CPU)
- [ ] Ports: `8888` + `5000`
- [ ] Cliquer "Deploy"
- [ ] Attendre 🟢 RUNNING
- [ ] Ouvrir l'URL Jupyter

---

## 🐛 Erreurs Communes

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Image not found" | Image pas publique | Docker Hub → Public |
| Pod reste 🟡 | Pas de crédit | Ajouter carte bancaire |
| "GPU unavailable" | Pas dispo | Essayer autre GPU |
| Jupyter error | Port mal config | Re-deploy avec ports |

---

## 💡 Tips

**Déboguer**: RunPod Console → Pod → Logs

**Économiser**: CPU coûte ~$0.02/h, GPU ~$0.24/h

**Sauvegarder**: Pod → "Save as Template" avant terminer

**SSH**: RunPod Console → Pod → "Connect" → SSH

---

## 📞 Besoin d'aide?

- RunPod Support: https://runpod.io/console/support
- Docs: https://docs.runpod.io/
- API: https://docs.runpod.io/api/

---

## ✅ Résumé

```
1. Aller sur https://www.runpod.io/console/pods
2. Cliquer Deploy → Any Template
3. Remplir: user/btc-xgb-poc:latest
4. GPU: 1 × RTX_4090
5. Ports: 8888, 5000
6. Cliquer Deploy
7. Attendre 🟢 RUNNING (3-5 min)
8. Ouvrir URL Jupyter
9. Voilà! 🎉
```

Durée totale: **~10 minutes** (2 min setup + 5 min démarrage + 3 min accès)
