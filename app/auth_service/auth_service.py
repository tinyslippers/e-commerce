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


def generate_token(user_id: int, username: str) -> str:
    """
    Génère un JWT avec un 'sub' (subject = user_id) et un username.
    """
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
        "iat": datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    # PyJWT >= 2 retourne déjà une str, mais au cas où :
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

    token = generate_token(DUMMY_USER["id"], DUMMY_USER["username"])

    return jsonify({
        "access_token": token,
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
        # Pour le TP : on lit le payload sans vérifier la signature.
        # En production, il faudrait garder la vérification avec SECRET_KEY.
        decoded = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception as e:
        print("DEBUG /verify decode error:", repr(e))
        return jsonify({"valid": False, "error": "Token invalide"}), 401

    # decoded contient le payload du token (sub, username, exp, etc.)
    user_info = {
        "sub": decoded.get("sub"),
        "username": decoded.get("username"),
    }

    return jsonify({"valid": True, "user": user_info}), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Petit endpoint de santé pour vérifier que le service tourne.
    """
    return jsonify({"status": "ok", "service": "auth_service"}), 200


if __name__ == "__main__":
    # Lance le service d'auth sur le port 5001
    app.run(host="127.0.0.1", port=5001, debug=True)