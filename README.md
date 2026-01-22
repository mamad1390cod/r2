
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
| `PAYPAL_SANDBOX` | Use Sandbox mode? | `True` or `False` |
| `PAYPAL_SANDBOX_CLIENT_ID` | PayPal Sandbox Client ID | `Af2z...` |
| `PAYPAL_SANDBOX_SECRET` | PayPal Sandbox Secret | `EIId...` |
| `PAYPAL_LIVE_CLIENT_ID` | PayPal Live Client ID (Production) | `AXyz...` |
| `PAYPAL_LIVE_SECRET` | PayPal Live Secret (Production) | `ELmn...` |
| `TELEGRAM_BOT_TOKEN` | Bot Token from BotFather | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Chat ID to receive orders | `-100123...` |

### 💳 PayPal Mode Switching

- **`PAYPAL_SANDBOX=True`** → Uses Sandbox credentials with `api-m.sandbox.paypal.com`
- **`PAYPAL_SANDBOX=False`** → Uses Live credentials with `api-m.paypal.com`

> ⚠️ **Important**: For production, set `PAYPAL_SANDBOX=False` and provide your LIVE credentials.

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