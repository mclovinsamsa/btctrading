# RunPod - Créer et Sauvegarder un Template Personnalisé

## 🎯 Objectif
Créer un template réutilisable pour lancer rapidement des pods avec la même configuration.

---

## 📋 Étape 1: Créer votre premier Pod

### 1.1 Aller sur RunPod Console
```
https://www.runpod.io/console/pods
```

### 1.2 Cliquer "Deploy"
```
Gros bouton bleu "Deploy"
```

### 1.3 Sélectionner "Any Template"
```
Chercher "Any Template" et cliquer
```

### 1.4 Remplir le formulaire

| Champ | Valeur |
|-------|--------|
| **Container Image** | `mclovinette/btc-xgb-poc:latest` |
| **Container Disk** | `20` GB |
| **GPU Count** | `1` |
| **GPU Type** | `RTX_4090` (ou autre) |

### 1.5 Ajouter les Ports

```
→ "Add Port" (ou "Add Mapped Port")

Port 1:
  Container Port: 8888
  [Generate]

Port 2:
  Container Port: 5000
  [Generate]
```

### 1.6 Configuration Avancée (Optionnel)

Laisser par défaut pour l'instant.

### 1.7 Déployer

```
[Deploy] ← Cliquer
```

**Attendre 3-5 minutes** que le pod démarre ⏳

---

## 💾 Étape 2: Sauvegarder comme Template

Une fois **le pod en `RUNNING`**:

### 2.1 Aller dans la RunPod Console
```
https://www.runpod.io/console/pods
```

### 2.2 Cliquer sur votre Pod

```
Vous voyez un panel: Details, Logs, etc.
```

### 2.3 Chercher "Save as Template"

```
En haut du panel → [Save as Template]
ou dans le menu → ⋮ (trois points) → "Save as Template"
```

### 2.4 Remplir les infos

```
Template Name:        BTC-XGB-POC-Template
Description:          XGBoost + PyTorch 2.8 with Jupyter Lab
Category:             Machine Learning
```

### 2.5 Sauvegarder

```
[Save Template] ← Cliquer
```

**Voilà!** Votre template est créé ✨

---

## 🚀 Étape 3: Réutiliser votre Template

### La prochaine fois que vous voulez un pod:

1. **Aller sur**: https://www.runpod.io/console/pods

2. **Cliquer "Deploy"**

3. **Chercher "My Templates"** (ou votre username)

4. **Sélectionner "BTC-XGB-POC-Template"**

```
L'image et configuration se remplissent automatiquement!
```

5. **Cliquer "Deploy"**

6. **C'est prêt!** 🎉

---

## 📖 Interface RunPod - Où trouver "Save as Template"

### Option 1: Via le menu du Pod

```
Mon Pod: btc-xgb-poc
Status: 🟢 RUNNING

[Connect] [Logs] [Stop] [Delete] [⋮]
                            ↑ Cliquer les 3 points

→ "Save as Template"
```

### Option 2: Via le panel principal

```
Si vous voyez un bouton "Save as Template" directement
→ Cliquer!
```

---

## 🔍 Vérifier votre Template

1. **Aller sur**: https://www.runpod.io/console/templates

2. **Vous devriez voir**:
   ```
   BTC-XGB-POC-Template
   Machine Learning
   Last modified: today
   ```

3. **Vous pouvez maintenant**:
   - Edit → Modifier la config
   - Deploy → Créer un nouveau pod
   - Delete → Supprimer le template

---

## 🎯 Workflow Complet - Vue d'ensemble

```
1. Créer le pod initial
   ↓
2. Configurer (GPU, ports, etc.)
   ↓
3. Lancer (Deploy)
   ↓
4. Attendre qu'il soit RUNNING
   ↓
5. Save as Template
   ↓
6. À l'avenir: Deploy from Template (2 clics!) 🚀
```

---

## 💡 Tips Avancés

### Éditer votre Template après création

1. **Console → Templates**

2. **Cliquer sur votre template**

3. **Cliquer "Edit"**

4. **Modifier les champs** (GPU type, disk size, ports, etc.)

5. **Sauvegarder** [Save Template]

```
Les nouveaux pods utilisés déjà cette config modifiée
```

### Dupliquer un Template

```
Templates → Cliquer le template → [⋮] → "Duplicate"
```

Utile pour créer des variantes (CPU vs GPU, différentes GPUs, etc.)

### Rendre le Template public (avec d'autres)

```
Templates → Cliquer template → [Edit]
→ Visibility: "Community"
→ Save
```

Les autres utilisateurs RunPod peuvent maintenant l'utiliser!

---

## 🔄 Scénarios d'Utilisation

### Scénario 1: Formation rapide
```
Besoin: Spin up un pod rapidement
Action: Deploy from Template → 1 clic + 5 min
Résultat: Pod prêt avec XGBoost + Jupyter
```

### Scénario 2: Tests multiples
```
Besoin: Tester plusieurs GPUs
Action: Edit template → Change GPU type → Deploy
Résultat: Test avec RTX 4090, A40, H100 sans reconfigurer
```

### Scénario 3: Production
```
Besoin: Déployer exactement la même config à chaque fois
Action: Save as Template → toujours deploy celui-ci
Résultat: Cohérence garantie pour tous les pods
```

---

## 📊 Exemple de Template Complet

```json
{
  "name": "BTC-XGB-POC-Template",
  "description": "XGBoost + PyTorch 2.8 + Jupyter Lab",
  "containerImage": "mclovinette/btc-xgb-poc:latest",
  "gpuCount": 1,
  "gpuType": "RTX_4090",
  "containerDiskInGb": 20,
  "volumeInGb": 10,
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
  "environmentVariables": [
    {
      "key": "JUPYTER_ENABLE_LAB",
      "value": "yes"
    }
  ]
}
```

---

## 🆘 Troubleshooting

| Problème | Solution |
|----------|----------|
| "Save as Template" pas visible | Le pod doit être en `RUNNING` d'abord |
| Template n'apparaît pas | Rafraîchir la page ou aller sur Templates |
| "Can't deploy from template" | Vérifier que l'image est publique |
| Modification template ne s'applique pas | Créer un NEW pod (les anciens gardent l'ancienne config) |

---

## 🎓 Après Sauvegarde

### Terminer le Pod initial (pour économiser)
```
Console → Pod → [Stop] ou [Delete]
```

### Relancer plus tard
```
Console → Deploy → My Templates → BTC-XGB-POC-Template → Deploy
```

### Voilà! Vous avez un template réutilisable ✨
```
Chaque fois: 5 minutes au lieu de 15 minutes de config!
```

---

## 📚 Ressources

- RunPod Templates Docs: https://docs.runpod.io/docs/templates
- Console: https://www.runpod.io/console/pods
- Templates Manager: https://www.runpod.io/console/templates
- Support: https://runpod.io/console/support
