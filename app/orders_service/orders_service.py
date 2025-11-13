

from flask import Flask, request, jsonify

app = Flask(__name__)

# Pour le TP : stockage en mémoire (disparaît à chaque redémarrage)
ORDERS = []


@app.route("/orders", methods=["POST"])
def create_order():
    """
    Crée une nouvelle commande.
    Attend un JSON du type :
    {
        "user_id": 1,
        "items": [ { "id": ..., "titre": ..., "prix": ..., "qty": ..., "subtotal": ... }, ... ],
        "total": 123.45,
        "transaction_id": "tx-...",
        "datetime": "2025-11-13T10:15:00Z"
    }
    """
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    items = data.get("items") or []
    total = data.get("total")
    transaction_id = data.get("transaction_id")
    dt_iso = data.get("datetime")

    if not user_id or not items or total is None:
        return jsonify({"error": "Champs manquants (user_id, items, total)."}), 400

    order_id = len(ORDERS) + 1
    order = {
        "id": order_id,
        "user_id": user_id,
        "transaction_id": transaction_id,
        "datetime": dt_iso,
        "total": total,
        "items": items,
    }
    ORDERS.append(order)

    return jsonify(order), 201


@app.route("/orders/<int:user_id>", methods=["GET"])
def list_orders_for_user(user_id: int):
    """
    Liste les commandes pour un utilisateur donné.
    Retourne un tableau de commandes avec la même structure que ci-dessus.
    """
    user_orders = [
        {
            "id": o["id"],
            "transaction_id": o["transaction_id"],
            "datetime": o["datetime"],
            "total": o["total"],
            "items": o["items"],
        }
        for o in ORDERS
        if o.get("user_id") == user_id
    ]
    return jsonify(user_orders), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Endpoint de santé pour vérifier que le service Orders tourne.
    """
    return jsonify({"status": "ok", "service": "orders_service"}), 200


if __name__ == "__main__":
    # Lance le service des commandes sur le port 5003
    app.run(host="127.0.0.1", port=5003, debug=True)