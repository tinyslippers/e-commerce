# E-Commerce — Microservices Flask  Baptiste RODRIGUES

Ce projet est une application e-commerce en **Python/Flask**, organisée en microservices simples :

* un service d’authentification
* un service de gestion des commandes
* une interface web Flask avec templates
* un système de panier, de commande et d’historique

---

## Fonctionnalités

### Authentification

* Connexion via formulaire
* Vérification des identifiants
* Stockage des utilisateurs (SQLite et fichier JSON)

### Boutique et Panier

* Affichage des articles
* Ajout et suppression du panier
* Confirmation de commande
* Historique des achats

### Architecture Microservices

```
e-commerce/
│
├── app/
│   ├── auth_service/
│   │   └── auth_service.py
│   ├── orders_service/
│   │   └── orders_service.py
│   ├── data/
│   │   ├── database.db
│   │   └── users.json
│   ├── templates/
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── cart.html
│   │   ├── articles.html
│   │   ├── confirm.html
│   │   ├── confirm_cart.html
│   │   ├── confirmation.html
│   │   └── history.html
│   ├── views.py
│   └── __init__.py
│
├── run.py
└── requirements.txt
```

---

## Installation et Lancement

### 1. Cloner le projet

```bash
git clone https://github.com/tinyslippers/e-commerce.git
cd e-commerce
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application

```bash
python run.py
```

Ouvrir ensuite dans un navigateur :

[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## Technologies Utilisées

* Python 3.13
* Flask
* SQLite
* HTML / Jinja2
* Architecture microservices minimaliste

---

## Améliorations Possibles

* Mise en place d’une authentification par JWT
* Passage à une base de données plus robuste (PostgreSQL, MongoDB…)
* Conteneurisation via Docker
* Ajout de tests unitaires
* Création d’une API REST complète
* Amélioration du système d’erreurs et des retours utilisateur

---

## Auteur

Baptiste Rodrigues (tinyslippers)
Étudiant en ingénierie, intéressé par le développement Python, Flask et les architectures logicielles modernes.

---

## Contribution

1. Fork du dépôt
2. Création d’une branche :

   ```bash
   git checkout -b feature-nouvelle-fonction
   ```
3. Commit et push
4. Ouverture d’une Pull Request

---

## Licence

Libre pour un usage éducatif ou personnel.
Pour un usage professionnel, merci de me contacter.
