import os

client_id = os.environ.get("CLIENT_ID", None)
client_secret = os.environ.get("CLIENT_SECRET", None)

phone = os.environ["PHONE"]
password = os.environ["PASSWORD"]
webhook_port = os.environ.get('WEBHOOK_PORT', 8000)
webhook_base_url = os.environ.get("WEBHOOK_BASE_URL", None)

token = os.environ["TOKEN"]
