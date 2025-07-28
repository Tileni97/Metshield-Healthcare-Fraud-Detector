import requests
import logging

FRESHDESK_DOMAIN = "nust-help.freshdesk.com"
FRESHDESK_API_KEY = "AgpnxILTvKcYjIspBF"
FRESHDESK_ENDPOINT = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"


def submit_freshdesk_ticket(
    subject: str,
    description: str,
    email: str = "alerts@metshield.ai",
    priority: int = 2,
):
    try:
        payload = {
            "subject": subject,
            "description": description,
            "email": email,
            "priority": priority,  # 1 = Low, 2 = Medium, 3 = High, 4 = Urgent
            "status": 2,  # Open
        }

        response = requests.post(
            FRESHDESK_ENDPOINT,
            auth=(FRESHDESK_API_KEY, "X"),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            logging.info("✅ Freshdesk ticket created successfully.")
        else:
            logging.error(
                f"❌ Failed to create Freshdesk ticket: {response.status_code} - {response.text}"
            )

    except Exception as e:
        logging.error(f"🔥 Error submitting ticket to Freshdesk: {e}")
