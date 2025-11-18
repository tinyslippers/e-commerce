from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from functools import wraps
import random
import time
import logging
from collections import Counter
from datetime import datetime
import requests

# Circuit breaker
import pybreaker

bp = Blueprint("main", __name__)

# ================== URLs des microservices ==================
AUTH_SERVICE_URL = "http://localhost:5001"
USER_SERVICE_URL = "http://localhost:5002"
ORDERS_SERVICE_URL = "http://localhost:5003"

# ================== Données “catalogue” en mémoire ==================
ARTICLES = [
    {"id": 1,  "titre": "Clavier mécanique",          "prix": 79.90},
    {"id": 2,  "titre": "Souris sans fil",            "prix": 39.90},
    {"id": 3,  "titre": "Écran 27\"",                 "prix": 229.00},
    {"id": 4,  "titre": "Casque audio fermé",         "prix": 99.00},
    {"id": 5,  "titre": "Casque audio ouvert",        "prix": 129.00},
    {"id": 6,  "titre": "Micro USB cardioïde",        "prix": 59.90},
    {"id": 7,  "titre": "Webcam 1080p 60fps",         "prix": 89.90},
    {"id": 8,  "titre": "Hub USB-C 8-en-1",           "prix": 49.90},
    {"id": 9,  "titre": "SSD NVMe 1To",               "prix": 99.90},
    {"id": 10, "titre": "Clé USB 128Go",              "prix": 19.90},
    {"id": 11, "titre": "Tapis de souris XL",         "prix": 24.90},
    {"id": 12, "titre": "Support écran aluminium",    "prix": 34.90},
    {"id": 13, "titre": "Station d’accueil USB-C",    "prix": 149.00},
    {"id": 14, "titre": "Chargeur GaN 65W",           "prix": 39.90},
    {"id": 15, "titre": "Câble USB-C 2m 100W",        "prix": 12.90},
]
ARTICLES_BY_ID = {a["id"]: a for a in ARTICLES}


# ================== Circuit Breaker ==================

logger = logging.getLogger(__name__)
breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=15, name="bank_api_breaker")

# ================== Helpers session/panier ==================

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        access_token = session.get("access_token")
        refresh_token = session.get("refresh_token")

        if not access_token:
            return redirect(url_for("main.login"))

        # Première tentative de vérification de l'access token
        try:
            resp = requests.post(
                f"{AUTH_SERVICE_URL}/verify",
                json={"token": access_token},
                timeout=2,
            )
        except requests.RequestException:
            # Si le service d'auth est down, on force une reconnexion
            session.clear()
            return redirect(url_for("main.login"))

        data = resp.json() if resp.content else {}

        if resp.status_code == 200 and data.get("valid"):
            # Token encore valide : on met à jour les infos utilisateur et on passe
            user_info = data.get("user", {})
            session["user_id"] = user_info.get("sub")
            if user_info.get("username"):
                session["username"] = user_info.get("username")
            return view_func(*args, **kwargs)

        # Ici : soit status != 200, soit valid == False
        error = data.get("error")

        # Si le token est expiré et qu'on a un refresh token, on tente un refresh
        if error == "Token expiré" and refresh_token:
            try:
                r = requests.post(
                    f"{AUTH_SERVICE_URL}/refresh",
                    json={"refresh_token": refresh_token},
                    timeout=2,
                )
            except requests.RequestException:
                session.clear()
                return redirect(url_for("main.login"))

            if r.status_code == 200 and r.content:
                new_data = r.json()
                new_access = new_data.get("access_token")
                if new_access:
                    # On met à jour le token d'accès et les infos utilisateur
                    session["access_token"] = new_access
                    session["user_id"] = new_data.get("user_id")
                    session["username"] = new_data.get("username")
                    # On laisse passer la requête protégée
                    return view_func(*args, **kwargs)

        # Dans tous les autres cas : on nettoie la session et on renvoie au login
        session.clear()
        return redirect(url_for("main.login"))

    return wrapper

def get_cart_counter() -> Counter:
    ids = session.get("cart", [])
    return Counter(ids)

def get_cart_items_and_total():
    cnt = get_cart_counter()
    items = []
    total = 0.0
    for aid, qty in cnt.items():
        art = ARTICLES_BY_ID.get(aid)
        if not art:
            continue
        subtotal = art["prix"] * qty
        total += subtotal
        items.append({
            "id": art["id"],
            "titre": art["titre"],
            "prix": art["prix"],
            "qty": qty,
            "subtotal": round(subtotal, 2),
        })
    return items, round(total, 2)

def cart_count() -> int:
    return len(session.get("cart", []))

# ================== Paiement simulé ==================

def _simulate_bank_charge(payload):
    # 45% d'échec pour forcer des cas breaker
    latency = random.uniform(0.05, 0.3)
    time.sleep(latency)
    if random.random() < 0.45:
        raise TimeoutError("La banque ne répond pas (simulé)")
    return {"status": "ok", "transaction_id": f"tx-{int(time.time())}"}

@breaker
def process_payment_with_breaker(payload):
    return _simulate_bank_charge(payload)

# ================== Routes ==================


@bp.route("/", methods=["GET", "POST"])
def login():
    """
    Login via Auth Service :
    - En POST, on envoie username/password à Auth Service
    - Si OK, on récupère un JWT que l'on stocke en session
    """
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            return render_template("login.html", error="Veuillez saisir un nom d’utilisateur et un mot de passe.")

        try:
            resp = requests.post(
                f"{AUTH_SERVICE_URL}/login",
                json={"username": username, "password": password},
                timeout=2,
            )
        except requests.RequestException:
            return render_template("login.html", error="Service d’authentification indisponible. Réessayez plus tard.")

        if resp.status_code != 200:
            data = resp.json() if resp.content else {}
            error_msg = data.get("error", "Identifiants invalides.")
            return render_template("login.html", error=error_msg)

        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            return render_template("login.html", error="Réponse invalide du service d’authentification.")

        # Stockage des tokens en session
        session["access_token"] = access_token
        refresh_token = data.get("refresh_token")
        if refresh_token:
            session["refresh_token"] = refresh_token

        # On garde username saisi pour l’affichage, en attendant de récupérer celui du token
        session["username"] = data.get("username", username)
        session["user_id"] = data.get("user_id")
        session.pop("cart", None)
        return redirect(url_for("main.articles"))

    return render_template("login.html")


# ----- Création de compte côté Gateway -----
@bp.route("/register", methods=["POST"])
def register():
    """
    Création de compte côté Gateway :
    - Récupère le formulaire de login.html
    - Appelle Auth Service /register
    - Si succès : stocke les tokens en session et redirige vers les articles
    - Si erreur : réaffiche login.html avec le message d'erreur
    """
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    email = (request.form.get("email") or "").strip()

    if not username or not password:
        return render_template("login.html", error="Nom d'utilisateur et mot de passe requis pour créer un compte.")

    payload = {
        "username": username,
        "password": password,
        "email": email,
    }

    try:
        resp = requests.post(
            f"{AUTH_SERVICE_URL}/register",
            json=payload,
            timeout=3,
        )
    except requests.RequestException:
        return render_template("login.html", error="Service d'inscription indisponible. Réessayez plus tard.")

    if resp.status_code not in (200, 201):
        data = resp.json() if resp.content else {}
        error_msg = data.get("error", "Erreur lors de la création du compte.")
        return render_template("login.html", error=error_msg)

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return render_template("login.html", error="Réponse invalide du service d'inscription.")

    # Stockage des tokens et infos utilisateur en session
    session["access_token"] = access_token
    if refresh_token:
        session["refresh_token"] = refresh_token
    session["username"] = data.get("username", username)
    session["user_id"] = data.get("user_id")
    session.pop("cart", None)

    return redirect(url_for("main.articles"))


@bp.route("/articles")
@login_required
def articles():
    username = session.get("username")
    return render_template("articles.html", username=username, articles=ARTICLES, cart_count=cart_count())


# ----- Sélection des articles (pas d’achat direct) -----

@bp.route("/acheter/<int:article_id>")
@login_required
def acheter(article_id: int):
    if article_id not in ARTICLES_BY_ID:
        abort(404)
    cart = session.get("cart", [])
    cart.append(article_id)
    session["cart"] = cart
    return redirect(url_for("main.panier"))

@bp.route("/panier/ajouter/<int:article_id>")
@login_required
def panier_ajouter(article_id: int):
    if article_id not in ARTICLES_BY_ID:
        abort(404)
    cart = session.get("cart", [])
    cart.append(article_id)
    session["cart"] = cart
    return redirect(url_for("main.articles"))

@bp.route("/panier")
@login_required
def panier():
    username = session.get("username")
    items, total = get_cart_items_and_total()
    return render_template("cart.html", username=username, items=items, total=total, cart_count=cart_count())

@bp.route("/panier/supprimer/<int:article_id>")
@login_required
def panier_supprimer(article_id: int):
    cart = session.get("cart", [])
    try:
        cart.remove(article_id)
    except ValueError:
        pass
    session["cart"] = cart
    return redirect(url_for("main.panier"))

@bp.route("/panier/vider")
@login_required
def panier_vider():
    session.pop("cart", None)
    return redirect(url_for("main.panier"))

@bp.route("/panier/payer", methods=["GET", "POST"])
@login_required
def panier_payer():
    username = session.get("username")
    user_id = session.get("user_id")
    items, total = get_cart_items_and_total()
    if not items:
        return redirect(url_for("main.panier"))

    try:
        res = process_payment_with_breaker({"type": "cart", "total": total, "count": len(items)})
    except pybreaker.CircuitBreakerError:
        error = "Le service bancaire ne répond pas actuellement. Réessayez dans quelques instants."
        return render_template("cart.html", username=username, items=items, total=total, error=error, cart_count=cart_count())
    except Exception as exc:
        logger.exception("Échec du paiement du panier : %s", exc)
        error = "Échec lors de la tentative de paiement (erreur réseau). Réessayez."
        return render_template("cart.html", username=username, items=items, total=total, error=error, cart_count=cart_count())

    dt_iso = datetime.utcnow().isoformat() + "Z"
    txid = res.get("transaction_id")

    # Envoi de la commande au Orders Service
    if not user_id:
        # Si pour une raison quelconque on n’a pas user_id en session, on tente de le récupérer via /verify
        token = session.get("access_token")
        if token:
            try:
                verify_resp = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"token": token}, timeout=2)
                if verify_resp.status_code == 200 and verify_resp.json().get("valid"):
                    session["user_id"] = verify_resp.json().get("user", {}).get("sub")
                    user_id = session["user_id"]
            except requests.RequestException:
                logger.exception("Impossible de récupérer user_id via Auth Service")

    order_payload = {
        "user_id": user_id,
        "items": items,
        "total": total,
        "transaction_id": txid,
        "datetime": dt_iso,
    }

    try:
        order_resp = requests.post(f"{ORDERS_SERVICE_URL}/orders", json=order_payload, timeout=2)
        if order_resp.status_code != 201:
            logger.error("Orders Service a retourné un statut inattendu: %s", order_resp.status_code)
    except requests.RequestException as exc:
        logger.exception("Erreur lors de l’appel au Orders Service: %s", exc)

    # pour confirmation
    session["last_order"] = {"items": items, "total": total}
    session.pop("cart", None)
    return redirect(url_for("main.confirmation_panier"))

@bp.route("/confirmation-panier")
@login_required
def confirmation_panier():
    username = session.get("username")
    order = session.pop("last_order", None)
    if not order:
        return redirect(url_for("main.panier"))
    return render_template("confirm_cart.html", username=username, items=order["items"], total=order["total"])

# ----- Historique -----

@bp.route("/historique")
@login_required
def historique():
    username = session.get("username")
    user_id = session.get("user_id")
    orders = []

    if not user_id:
        # On tente de récupérer user_id via Auth Service
        token = session.get("access_token")
        if token:
            try:
                verify_resp = requests.post(f"{AUTH_SERVICE_URL}/verify", json={"token": token}, timeout=2)
                if verify_resp.status_code == 200 and verify_resp.json().get("valid"):
                    session["user_id"] = verify_resp.json().get("user", {}).get("sub")
                    user_id = session["user_id"]
            except requests.RequestException:
                logger.exception("Impossible de récupérer user_id via Auth Service")

    if user_id:
        try:
            resp = requests.get(f"{ORDERS_SERVICE_URL}/orders/{user_id}", timeout=2)
            if resp.status_code == 200:
                orders = resp.json()
            else:
                logger.error("Orders Service /orders/%s a retourné le statut %s", user_id, resp.status_code)
        except requests.RequestException as exc:
            logger.exception("Erreur lors de l’appel au Orders Service: %s", exc)

    return render_template("history.html", username=username, orders=orders)

# (Page héritée de l’ancien flow — optionnel)
@bp.route("/confirmation/<int:article_id>")
@login_required
def confirmation(article_id: int):
    username = session.get("username")
    article = ARTICLES_BY_ID.get(article_id)
    if not article:
        abort(404)
    return render_template("confirmation.html", username=username, article=article)