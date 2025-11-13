import subprocess
import sys
import os
from app import app

if __name__ == "__main__":
    # Paths to microservices
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auth_path = os.path.join(base_dir, "app", "auth_service", "auth_service.py")
    orders_path = os.path.join(base_dir, "app", "orders_service", "orders_service.py")

    # Launch Auth Service
    subprocess.Popen([sys.executable, auth_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Launch Orders Service
    subprocess.Popen([sys.executable, orders_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    app.run(
        host="127.0.0.1",
        port=5050,
        debug=True
    )