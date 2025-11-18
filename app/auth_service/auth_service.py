from flask import Flask, request, jsonify
import secrets
import time

app = Flask(__name__)




DUMMY_USER = {
    "id": 1,
    "username": "baptiste",
    "password": "password123",  # en vrai : hashé !
    "email": "baptiste@example.com",
}

# Petite "base" d'utilisateurs en mémoire pour le TP
USERS = {
    DUMMY_USER["username"]: DUMMY_USER
}

# Stores en mémoire pour les tokens opaques (stateful, effacés au redémarrage)
SESSIONS = {}        # access_token -> {"sub": user_id, "username": ..., "exp": ...}
REFRESH_TOKENS = {}  # refresh_token -> {"sub": user_id, "username": ..., "exp": ...}


def generate_access_token(user_id: int, username: str) -> str:
    """
    Génère un token opaque d'accès valable 5 minutes.
    Le token est stocké en mémoire (stateful) dans SESSIONS.
    """
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "sub": user_id,
        "username": username,
        "exp": now + 300,  # 5 minutes
    }
    return token


def generate_refresh_token(user_id: int, username: str) -> str:
    """
    Génère un token opaque de refresh valable 1 heure.
    Le token est stocké en mémoire (stateful) dans REFRESH_TOKENS.
    """
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    REFRESH_TOKENS[token] = {
        "sub": user_id,
        "username": username,
        "exp": now + 3600,  # 1 heure
    }
    return token


@app.route("/login", methods=["POST"])
def login():
    """
    Authentification basique :
    - Reçoit { "username": "...", "password": "..." }
    - Vérifie par rapport à DUMMY_USER
    - Retourne un couple de tokens opaques (access + refresh) si OK
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Identifiants manquants"}), 400

    # On récupère l'utilisateur depuis la "base" en mémoire
    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Identifiants invalides"}), 401

    access_token = generate_access_token(user["id"], user["username"])
    refresh_token = generate_refresh_token(user["id"], user["username"])

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
    }), 200


# Endpoint de création de compte
@app.route("/register", methods=["POST"])
def register():
    """
    Création d'un nouvel utilisateur.
    Reçoit : { "username": "...", "password": "..." }
    Renvoie : access_token + refresh_token comme /login
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Champs username et password obligatoires."}), 400

    # Vérifier que le username n'est pas déjà pris
    if username in USERS:
        return jsonify({"error": "Nom d'utilisateur déjà utilisé."}), 400

    # Générer un nouvel id simple à partir des utilisateurs existants
    if USERS:
        new_id = max(int(u["id"]) for u in USERS.values()) + 1
    else:
        new_id = 1

    new_user = {
        "id": new_id,
        "username": username,
        "password": password,  # ⚠️ en vrai : à hasher !
        "email": f"{username}@example.com",
    }

    USERS[username] = new_user

    access_token = generate_access_token(new_user["id"], new_user["username"])
    refresh_token = generate_refresh_token(new_user["id"], new_user["username"])

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user_id": new_user["id"],
        "username": new_user["username"],
        "email": new_user["email"],
    }), 201


@app.route("/verify", methods=["POST"])
def verify():
    """
    Vérifie un token d'accès opaque (stateful).
    - Reçoit { "token": "..." }
    - Retourne { "valid": bool, "user": {...} } si OK
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    print("DEBUG /verify received token:", token)

    if not token:
        return jsonify({"error": "Token manquant"}), 400

    # Vérification stateful : on regarde si le token existe en mémoire
    session_info = SESSIONS.get(token)
    if not session_info:
        return jsonify({"valid": False, "error": "Token invalide ou révoqué"}), 401

    now = int(time.time())
    if session_info["exp"] < now:
        # On supprime le token expiré du store et on signale l'expiration
        del SESSIONS[token]
        return jsonify({"valid": False, "error": "Token expiré"}), 401

    user_info = {
        "sub": session_info["sub"],
        "username": session_info["username"],
    }

    return jsonify({"valid": True, "user": user_info}), 200


@app.route("/refresh", methods=["POST"])
def refresh():
    """
    Renvoie un nouvel access token à partir d'un refresh token opaque valide.
    """
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token manquant"}), 400

    # Vérification stateful du refresh token
    info = REFRESH_TOKENS.get(refresh_token)
    if not info:
        return jsonify({"error": "Refresh token invalide ou révoqué"}), 401

    now = int(time.time())
    if info["exp"] < now:
        # On supprime le refresh token expiré
        del REFRESH_TOKENS[refresh_token]
        return jsonify({"error": "Refresh token expiré"}), 401

    # On génère un nouveau access token pour le même utilisateur
    user_id = int(info["sub"])
    username = info["username"]
    new_access = generate_access_token(user_id, username)

    return jsonify({
        "access_token": new_access,
        "user_id": user_id,
        "username": username,
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Petit endpoint de santé pour vérifier que le service tourne.
    """
    return jsonify({"status": "ok", "service": "auth_service"}), 200


if __name__ == "__main__":
    # Lance le service d'auth sur le port 5001
    app.run(host="127.0.0.1", port=5001, debug=True)