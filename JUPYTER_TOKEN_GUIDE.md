# Jupyter Lab sur RunPod - Token & Authentification

## 🔐 Problème

Jupyter Lab demande un **token** ou **mot de passe** au démarrage.

---

## ✅ Solution 1: Récupérer le Token (Plus Sûr)

### 1.1 Aller sur RunPod Console
```
https://www.runpod.io/console/pods
```

### 1.2 Cliquer sur votre Pod

### 1.3 Aller dans "Logs"

```
[Connect] [Logs] ← Cliquer ici
```

### 1.4 Chercher le Token

Les logs affichent quelque chose comme:

```
...
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

    To access the server, open this file in a browser:
        file:///root/.jupyter/jupyter_lab_config.json
    Or copy and paste one of these URLs:
        http://localhost:8888/?token=abcd1234efgh5678ijkl9012mnop3456
        http://localhost:8888/?token=abcd1234efgh5678ijkl9012mnop3456
```

### 1.5 Copier le Token

Chercher: `token=xxxxxxxxxx`

```
Exemple: abcd1234efgh5678ijkl9012mnop3456
```

### 1.6 Utiliser le Token

1. **Ouvrir l'URL Jupyter** (depuis RunPod panel)
2. **Coller le token** quand demandé

```
URL: https://xxx-xxxxx.runpod.io:8888
Token: abcd1234efgh5678ijkl9012mnop3456
```

**C'est prêt!** ✨

---

## ⚡ Solution 2: Désactiver l'Authentification (Développement)

### Pour une déploiement de dév (plus simple):

1. **Retourner à votre machine**
2. **Modifier le Dockerfile**:

```dockerfile
# À la fin du Dockerfile, remplacer:
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

# Par:
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
```

3. **Re-build et re-push**:
```bash
docker build -t btc-xgb-poc:latest .
docker tag btc-xgb-poc:latest mclovinette/btc-xgb-poc:latest
docker push mclovinette/btc-xgb-poc:latest
```

4. **Redéployer le pod** avec la nouvelle image

Maintenant, **aucune authentification** 🔓

---

## 🔒 Solution 3: Mot de Passe Personnalisé (Production)

### 3.1 Générer un hash de mot de passe

Sur votre Mac, lancez:

```bash
python3 -c "from jupyter_server.auth import passwd; print(passwd('votre_mot_de_passe'))"
```

Ça génère quelque chose comme:
```
argon2:$argon2id$v=19$m=10000,t=10,p=8$XXXXX$XXXXX
```

### 3.2 Modifier le Dockerfile

```dockerfile
CMD ["jupyter", "lab", \
    "--ip=0.0.0.0", \
    "--port=8888", \
    "--no-browser", \
    "--allow-root", \
    "--NotebookApp.password='argon2:$argon2id$v=19$m=10000,t=10,p=8$XXXXX$XXXXX'"]
```

### 3.3 Re-build et push

```bash
docker build -t btc-xgb-poc:latest .
docker tag btc-xgb-poc:latest mclovinette/btc-xgb-poc:latest
docker push mclovinette/btc-xgb-poc:latest
```

### 3.4 Redéployer

Maintenant Jupyter demande le **mot de passe** que vous avez défini 🔐

---

## 📋 Méthodes Rapides - Comparaison

| Méthode | Sécurité | Facilité | Usage |
|---------|----------|----------|-------|
| Token depuis logs | ⭐⭐⭐ | ⭐⭐ | Développement |
| Sans authentification | ❌ | ⭐⭐⭐ | Dev local uniquement |
| Mot de passe | ⭐⭐ | ⭐⭐ | Production |

---

## 🎯 Pour vous maintenant:

### Étape 1: Récupérer le Token
```
RunPod Console → Pod → [Logs]
Chercher: token=xxxxx
```

### Étape 2: Copier en entier
```
http://localhost:8888/?token=abcd1234efgh5678ijkl9012mnop3456
```

### Étape 3: Ouvrir dans le navigateur
```
Remplacer localhost par votre URL RunPod
https://xxx-xxxxx.runpod.io:8888/?token=abcd1234efgh5678ijkl9012mnop3456
```

### Étape 4: Accepter

Jupyter Lab s'ouvre! 🎉

---

## 🔄 Alternative: Utiliser SSH

Si Jupyter pose problème, vous pouvez aussi utiliser SSH:

```bash
# Depuis RunPod, copier l'URL SSH
ssh -i ~/.ssh/id_rsa root@xxx-xxxxx.runpod.io -p XXXXX
```

Puis accéder à Jupyter via l'IP locale ou SSH tunneling.

---

## ❓ FAQ

**Q: Où sont les logs exactement?**
```
Console → Pod → [Connect] → [Logs]
Ou directement dans le panel du pod
```

**Q: Le token change chaque redémarrage?**
```
Oui, si vous ne le configurez pas en dur.
Mais il reste le même pour la durée de vie du pod.
```

**Q: Puis-je changer le mot de passe après?**
```
Oui, mais faut relancer le pod avec une nouvelle image Docker.
```

**Q: C'est quoi `--allow-root`?**
```
Permet à Jupyter de tourner en root (container RunPod).
Nécessaire pour RunPod.
```

---

## 🚀 Checkpoints

- [ ] Ouvrir les Logs du pod
- [ ] Trouver le token: `token=xxxxx`
- [ ] Copier l'URL complète avec token
- [ ] Accéder à Jupyter Lab
- [ ] C'est prêt! 🎉

---

## 💾 Fichier de Configuration Alternative

Pour plus de contrôle, créez `/app/jupyter_config.py`:

```python
# Configuration Jupyter
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.allow_remote_access = True
c.ServerApp.allow_root = True

# Authentification
c.ServerApp.token = ''  # Sans token
c.ServerApp.password = ''  # Sans mot de passe
```

Puis dans le Dockerfile:
```dockerfile
COPY jupyter_config.py /root/.jupyter/

CMD ["jupyter", "lab", "--config=/root/.jupyter/jupyter_config.py"]
```

---

## 📚 Ressources

- Jupyter Config: https://jupyter-server.readthedocs.io/
- RunPod Docs: https://docs.runpod.io/
- Security Best Practices: https://jupyter-server.readthedocs.io/en/latest/operators/security.html
