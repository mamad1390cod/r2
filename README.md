# Royal Restaurant (FastAPI + Railway)

A luxury food ordering system built with Python (FastAPI) and Vanilla JS.

## 🚀 Deployment on Railway

1.  **Fork/Clone** this repository.
2.  **Create a New Project** on Railway.
3.  **Deploy from Repo**.
4.  **Add Variables** (Settings > Variables):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `ADMIN_TOKEN` | Secure token for admin panel | `MySuperSecretToken2024` |
| `PAYPAL_CLIENT_ID` | PayPal REST API Client ID | `Af2z...` |
| `PAYPAL_SECRET` | PayPal REST API Secret | `EIId...` |
| `PAYPAL_SANDBOX` | Use Sandbox mode? | `True` or `False` |
| `TELEGRAM_BOT_TOKEN` | Bot Token from BotFather | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Chat ID to receive orders | `-100123...` |

## 📂 Project Structure

- `main.py`: Main server file (FastAPI).
- `client.html`: Customer frontend.
- `admin.html`: Admin panel (requires Token).
- `data.json`: Stores data (Note: Resets on redeploy in Railway unless using a Volume).

## 🔒 Security

- **Admin Access**: The Admin Panel is protected. You must enter the `ADMIN_TOKEN` defined in your environment variables to access the dashboard.
- **Payment**: All calculations happen server-side.
- **Secrets**: No secrets are stored in the code.

## 🛠 Local Development

```bash
pip install -r requirements.txt
python main.py
```