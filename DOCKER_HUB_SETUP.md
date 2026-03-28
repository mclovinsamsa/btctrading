# Docker Hub - Setup Complet

## 🔐 Créer un compte Docker Hub (Gratuit)

### Étape 1: Aller sur Docker Hub
```
https://hub.docker.com
```

### Étape 2: Cliquer "Sign Up"
```
Boutton en haut à droite → "Sign Up"
```

### Étape 3: Remplir le formulaire
```
Docker ID:        samybelkaid          ← C'est votre USERNAME
Email:            votre@email.com
Password:         votre_mot_de_passe
```

✅ **Valider l'email** (vérifier votre boîte mail)

---

## 💡 Comprendre "votreusername"

### Avant (template):
```
votreusername/btc-xgb-poc:latest
```

### Après (exemple réel):
```
samybelkaid/btc-xgb-poc:latest
                ↑ C'est votre Docker ID
```

### Autre exemple:
```
John123/btc-xgb-poc:latest
```

---

## 🔗 Trouver votre Docker ID

1. **Aller sur**: https://hub.docker.com
2. **Cliquer votre profil** (haut à droite)
3. **Voir "Account Settings"**
4. **Copier "Docker ID"** ou **"Username"**

```
Exemple:
Docker ID: samybelkaid  ← C'est celui-ci!
```

---

## 🚀 Se connecter depuis votre Mac

### Étape 1: Ouvrir Terminal
```bash
docker login
```

### Étape 2: Entrer vos identifiants
```
Username: samybelkaid          ← Votre Docker ID
Password: votre_mot_de_passe   ← Votre mot de passe Docker Hub

Login Succeeded!  ✅
```

---

## 📦 Pousser votre image (Workflow complet)

### 1️⃣ Build l'image
```bash
cd ~/btc_xgb_poc
docker build -t btc-xgb-poc:latest .
```

### 2️⃣ Tagger avec votre username
```bash
docker tag btc-xgb-poc:latest samybelkaid/btc-xgb-poc:latest
                               ↑ REMPLACER PAR VOTRE USERNAME
```

### 3️⃣ Pousser sur Docker Hub
```bash
docker push samybelkaid/btc-xgb-poc:latest
```

**Ça prend 5-10 minutes** ☕

### 4️⃣ Vérifier sur Docker Hub
```
https://hub.docker.com/r/samybelkaid/btc-xgb-poc
```

Vous devriez voir votre image listée! ✨

---

## 📋 Checklist

- [ ] Compte Docker Hub créé: https://hub.docker.com
- [ ] Email vérifié
- [ ] Docker ID noté: `samybelkaid` (exemple)
- [ ] `docker login` réussi
- [ ] Image taguée: `samybelkaid/btc-xgb-poc:latest`
- [ ] Image poussée: `docker push samybelkaid/btc-xgb-poc:latest`
- [ ] Image visible sur: https://hub.docker.com/r/samybelkaid/btc-xgb-poc

---

## 🔒 Rendre l'image PUBLIC

**Important**: L'image doit être **publique** pour que RunPod puisse la pull!

### Par défaut: PRIVÉE

Pour la rendre publique:

1. **Aller sur**: https://hub.docker.com/r/samybelkaid/btc-xgb-poc
2. **Cliquer "Settings"**
3. **Trouver "Repository Visibility"**
4. **Sélectionner "Public"**
5. **Sauvegarder**

```
Visibility: Public ✅
```

---

## ⚡ Commandes Rapides (Copy-Paste)

```bash
# 1. Se connecter
docker login
# → Entrer username et password

# 2. Builder
docker build -t btc-xgb-poc:latest .

# 3. Tagger (remplacer samybelkaid par votre username!)
docker tag btc-xgb-poc:latest samybelkaid/btc-xgb-poc:latest

# 4. Pousser
docker push samybelkaid/btc-xgb-poc:latest

# 5. Vérifier
# https://hub.docker.com/r/samybelkaid/btc-xgb-poc
```

---

## 🔍 Vérifier votre username

```bash
# Voir votre username Docker local
cat ~/.docker/config.json | grep -A 2 'auths'

# Ou simplement:
docker info | grep User
```

---

## ❌ Erreurs Courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| "denied: requested access to..." | Image privée | Rendre publique |
| "no such file or directory" | Pas connecté | `docker login` |
| "authentication required" | Login échoué | `docker logout` puis `docker login` |
| "no such image" | Mauvais tag | Vérifier le tag exact |

---

## 📚 Résumé

```
1. Créer compte Docker Hub gratuit: https://hub.docker.com
2. Votre Docker ID = votreusername (ex: samybelkaid)
3. docker login (entrer identifiants)
4. docker build -t btc-xgb-poc:latest .
5. docker tag btc-xgb-poc:latest samybelkaid/btc-xgb-poc:latest
6. docker push samybelkaid/btc-xgb-poc:latest
7. Vérifier: https://hub.docker.com/r/samybelkaid/btc-xgb-poc
8. Rendre PUBLIC
9. Utiliser sur RunPod: samybelkaid/btc-xgb-poc:latest
```

---

## 💡 Tips

### Garder le login
```bash
# Pour éviter de relancer docker login:
docker logout  # Logout d'abord
docker login   # Re-login avec "Remember me"
```

### Lister vos images locales
```bash
docker images | grep btc
```

### Voir les logs de push
```bash
# Pendant le push, voir la progression:
docker push samybelkaid/btc-xgb-poc:latest --verbose
```

### Alternative: GitHub Container Registry (GHCR)
Si vous préférez GitHub au lieu de Docker Hub:
```bash
docker tag btc-xgb-poc:latest ghcr.io/samybelkaid/btc-xgb-poc:latest
docker push ghcr.io/samybelkaid/btc-xgb-poc:latest
```

---

## 🎯 Prochaines étapes (après push)

1. ✅ Image sur Docker Hub
2. → RunPod Console
3. → Deploy → Any Template
4. → Image: `samybelkaid/btc-xgb-poc:latest`
5. → Enjoy!
