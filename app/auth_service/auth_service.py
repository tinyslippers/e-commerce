from flask import Flask, request, jsonify
import jwt
import datetime

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


def generate_access_token(user_id: int, username: str) -> str:
    """
    Génère un access token valable 5 minutes.
    """
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def generate_refresh_token(user_id: int, username: str) -> str:
    """
    Génère un refresh token valable 1 heure.
    """
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
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

    # Vérification ultra simplifiée : un seul user en dur
    if username != DUMMY_USER["username"] or password != DUMMY_USER["password"]:
        return jsonify({"error": "Identifiants invalides"}), 401

    access_token = generate_access_token(DUMMY_USER["id"], DUMMY_USER["username"])
    refresh_token = generate_refresh_token(DUMMY_USER["id"], DUMMY_USER["username"])

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user_id": DUMMY_USER["id"],
        "username": DUMMY_USER["username"],
        "email": DUMMY_USER["email"],
    }), 200


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
        decoded = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp"]}
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"valid": False, "error": "Token expiré"}), 401
    except jwt.InvalidTokenError as e:
        print("DEBUG /verify invalid token:", repr(e))
        return jsonify({"valid": False, "error": "Token invalide"}), 401

    if decoded.get("type") != "access":
        return jsonify({"valid": False, "error": "Mauvais type de token"}), 401

    # decoded contient le payload du token (sub, username, exp, etc.)
    user_info = {
        "sub": decoded.get("sub"),
        "username": decoded.get("username"),
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
        decoded = jwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp"]}
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expiré"}), 401
    except jwt.InvalidTokenError as e:
        print("DEBUG /refresh invalid token:", repr(e))
        return jsonify({"error": "Refresh token invalide"}), 401

    if decoded.get("type") != "refresh":
        return jsonify({"error": "Mauvais type de token"}), 401

    new_access = generate_access_token(decoded["sub"], decoded["username"])

    return jsonify({
        "access_token": new_access,
        "user_id": decoded["sub"],
        "username": decoded["username"],
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