from flask import Flask, request, jsonify
from authlib.jose import jwt
import datetime
from authlib.jose.errors import ExpiredTokenError, JoseError
import time

app = Flask(__name__)

# Clé secrète pour signer les JWT (à NE PAS exposer en prod)
SECRET_KEY = "change-me-super-secret"

# Pour le TP : un "vrai-faux" user en dur
# Tu pourras plus tard le remplacer par une vraie base ou un appel au User Service.

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


def generate_access_token(user_id: int, username: str) -> str:
    """
    Génère un access token (JWT) valable 5 minutes avec Authlib.
    """
    now = int(time.time())
    header = {"alg": "HS256"}
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + 300,  # 5 minutes
    }
    token = jwt.encode(header, payload, SECRET_KEY)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def generate_refresh_token(user_id: int, username: str) -> str:
    """
    Génère un refresh token (JWT) valable 1 heure avec Authlib.
    """
    now = int(time.time())
    header = {"alg": "HS256"}
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "iat": now,
        "exp": now + 3600,  # 1 heure
    }
    token = jwt.encode(header, payload, SECRET_KEY)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@app.route("/login", methods=["POST"])
def login():
    """
    Authentification basique :
    - Reçoit { "username": "...", "password": "..." }
    - Vérifie par rapport à DUMMY_USER
    - Retourne un JWT si OK
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
    Vérifie un JWT.
    - Reçoit { "token": "..." }
    - Retourne { "valid": bool, "user": {...} } si OK
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    print("DEBUG /verify received token:", token)

    if not token:
        return jsonify({"error": "Token manquant"}), 400

    try:
        claims = jwt.decode(token, SECRET_KEY)
        # Valide exp, iat, etc. ; lève ExpiredTokenError si expiré
        claims.validate()
    except ExpiredTokenError:
        return jsonify({"valid": False, "error": "Token expiré"}), 401
    except JoseError as e:
        print("DEBUG /verify invalid token:", repr(e))
        return jsonify({"valid": False, "error": "Token invalide"}), 401

    if claims.get("type") != "access":
        return jsonify({"valid": False, "error": "Mauvais type de token"}), 401

    # claims contient le payload du token (sub, username, exp, etc.)
    user_info = {
        "sub": claims.get("sub"),
        "username": claims.get("username"),
    }

    return jsonify({"valid": True, "user": user_info}), 200


@app.route("/refresh", methods=["POST"])
def refresh():
    """
    Renvoie un nouvel access token à partir d'un refresh token valide.
    """
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token manquant"}), 400

    try:
        claims = jwt.decode(refresh_token, SECRET_KEY)
        claims.validate()
    except ExpiredTokenError:
        return jsonify({"error": "Refresh token expiré"}), 401
    except JoseError as e:
        print("DEBUG /refresh invalid token:", repr(e))
        return jsonify({"error": "Refresh token invalide"}), 401

    if claims.get("type") != "refresh":
        return jsonify({"error": "Mauvais type de token"}), 401

    new_access = generate_access_token(int(claims["sub"]), claims["username"])

    return jsonify({
        "access_token": new_access,
        "user_id": claims["sub"],
        "username": claims["username"],
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