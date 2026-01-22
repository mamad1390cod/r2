
import os
import json
import logging
import httpx
import uvicorn
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Depends, status, UploadFile, File, Header
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load Env (for local dev)
load_dotenv()

# ============ Configuration ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
CLIENT_FILE = os.path.join(BASE_DIR, 'client.html')
ADMIN_FILE = os.path.join(BASE_DIR, 'admin.html')
SUCCESS_FILE = os.path.join(BASE_DIR, 'success.html')

# Environment Variables (Secrets)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "mamad1390") # Default for safety
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ============ PayPal Configuration ============
# Set PAYPAL_SANDBOX to "True" for testing, "False" for production
PAYPAL_SANDBOX = os.getenv("PAYPAL_SANDBOX", "True").lower() == "true"

# Sandbox Credentials (for testing)
PAYPAL_SANDBOX_CLIENT_ID = os.getenv("PAYPAL_SANDBOX_CLIENT_ID")
PAYPAL_SANDBOX_SECRET = os.getenv("PAYPAL_SANDBOX_SECRET")
# Live Credentials (for production)
PAYPAL_LIVE_CLIENT_ID = os.getenv("PAYPAL_LIVE_CLIENT_ID")
PAYPAL_LIVE_SECRET = os.getenv("PAYPAL_LIVE_SECRET")

# Select credentials based on mode
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RoyalRestaurant")

if PAYPAL_SANDBOX:
    PAYPAL_CLIENT_ID = PAYPAL_SANDBOX_CLIENT_ID
    PAYPAL_SECRET = PAYPAL_SANDBOX_SECRET
    PAYPAL_API_BASE = 'https://api-m.sandbox.paypal.com'
else:
    PAYPAL_CLIENT_ID = PAYPAL_LIVE_CLIENT_ID
    PAYPAL_SECRET = PAYPAL_LIVE_SECRET
    PAYPAL_API_BASE = 'https://api-m.paypal.com'
    logger.info("💳 PayPal running in LIVE mode")

OMR_TO_USD_RATE = 2.6

OMR_TO_USD_RATE = 2.6

# ============ FastAPI App ============
app = FastAPI(title="Royal Restaurant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Security ============
async def verify_admin(x_admin_token: str = Header(None)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Admin Token")
    return True

# ============ Data Models ============
class Translatable(BaseModel):
    fa: str
    en: str
    ar: str

class Product(BaseModel):
    id: str
    name: Translatable
    description: Translatable
    price: float
    discount: int = 0
    category: str
    image: str

class Category(BaseModel):
    id: str
    name: Translatable

class CartItem(BaseModel):
    id: str
    quantity: int

class Customer(BaseModel):
    firstName: str
    lastName: str
    phone: str
    address: str
    location: Optional[str] = None
    notes: Optional[str] = None
    contactMethod: str = "whatsapp"
    deliveryType: str = "delivery"

class OrderRequest(BaseModel):
    customer: Customer
    items: List[CartItem]

# ============ Data Manager ============
class DataManager:
    def __init__(self):
        self.ensure_data_file()

    def ensure_data_file(self):
        if not os.path.exists(DATA_FILE):
            initial_data = {
                "products": [],
                "categories": [],
                "orders": []
            }
            try:
                self.save_data(initial_data)
                self.seed_data()
            except Exception as e:
                logger.error(f"Error creating data file: {e}")

    def load_data(self):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"products": [], "categories": [], "orders": []}

    def save_data(self, data):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def seed_data(self):
        data = self.load_data()
        if not data["categories"]:
            data["categories"] = [
                {"id": "1", "name": {"fa": "پیش غذا", "en": "Appetizers", "ar": "المقبلات"}},
                {"id": "2", "name": {"fa": "غذای اصلی", "en": "Main Course", "ar": "الطبق الرئيسي"}},
            ]
        if not data["products"]:
            data["products"] = [
                {
                    "id": "1",
                    "name": {"fa": "استیک فیله مینیون", "en": "Filet Mignon Steak", "ar": "ستيك فيليه مينيون"},
                    "description": {"fa": "استیک گوساله درجه یک", "en": "Premium beef steak", "ar": "ستيك لحم بقري ممتاز"},
                    "price": 15.5,
                    "discount": 10,
                    "category": "2",
                    "image": "https://images.unsplash.com/photo-1600891964092-4316c288032e?w=400"
                }
            ]
        self.save_data(data)

db = DataManager()

# ============ Services ============
class PayPalService:
    async def get_access_token(self):
        if not PAYPAL_CLIENT_ID or not PAYPAL_SECRET:
            logger.error("PayPal credentials missing")
            return None
            
        async with httpx.AsyncClient() as client:
            try:
                auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
                data = {"grant_type": "client_credentials"}
                response = await client.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", auth=auth, data=data)
                response.raise_for_status()
                return response.json()["access_token"]
            except Exception as e:
                logger.error(f"PayPal Token Error: {e}")
                raise

    async def create_payment(self, total_usd: float, return_url: str, cancel_url: str):
        token = await self.get_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": f"{total_usd:.2f}"
                }
            }],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                "user_action": "PAY_NOW"
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PAYPAL_API_BASE}/v2/checkout/orders", headers=headers, json=order_data)
            response.raise_for_status()
            return response.json()

    async def capture_payment(self, order_id: str):
        token = await self.get_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture", headers=headers)
            response.raise_for_status()
            return response.json()

class TelegramService:
    async def send_order(self, order: dict):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials missing, skipping notification")
            return

        items_text = "\n".join([f"• {item['name']['fa']} × {item['quantity']} = {item['price']*item['quantity']:.2f} OMR" for item in order['items']])
        message = f"""
🛒 *سفارش جدید* (#{order['id']})

👤 *مشتری:* {order['customer']['firstName']} {order['customer']['lastName']}
📞 *تلفن:* {order['customer']['phone']}
📍 *آدرس:* {order['customer']['address']}
{f"🗺 *لوکیشن:* {order['customer']['location']}" if order['customer']['location'] else ""}

📦 *محصولات:*
{items_text}

💰 *مبلغ کل:* {order['total_omr']:.2f} OMR
💵 *پرداخت شده:* {order['total_usd']:.2f} USD

🚚 *تحویل:* {'ارسال' if order['customer']['deliveryType'] == 'delivery' else 'حضوری'}
📝 *توضیحات:* {order['customer']['notes'] or '-'}
        """
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload)
        except Exception as e:
            logger.error(f"Telegram error: {e}")

paypal_service = PayPalService()
telegram_service = TelegramService()

# ============ Routes ============

@app.get("/")
async def read_root():
    return FileResponse(CLIENT_FILE)

@app.get("/admin")
async def read_admin():
    # We serve the HTML, but data fetch will fail without Token
    return FileResponse(ADMIN_FILE)

@app.get("/success")
async def read_success():
    return FileResponse(SUCCESS_FILE)

# --- Public API Endpoints ---

@app.get("/api/data")
async def get_data():
    data = db.load_data()
    return {
        "products": data["products"],
        "categories": data["categories"]
    }

# --- Protected Admin API Endpoints ---

@app.post("/api/admin/login")
async def admin_login(payload: Dict[str, str]):
    # This endpoint verifies if the entered token is correct
    if payload.get("token") == ADMIN_TOKEN:
        return {"status": "success"}
    raise HTTPException(status_code=401, detail="Invalid Token")

@app.get("/api/admin/full-data")
async def get_admin_data(authorized: bool = Depends(verify_admin)):
    return db.load_data()

@app.post("/api/admin/product")
async def save_product(product: Product, authorized: bool = Depends(verify_admin)):
    data = db.load_data()
    existing = next((i for i, p in enumerate(data["products"]) if p["id"] == product.id), None)
    
    product_dict = product.dict()
    if existing is not None:
        data["products"][existing] = product_dict
    else:
        data["products"].append(product_dict)
    
    db.save_data(data)
    return {"status": "success"}

@app.delete("/api/admin/product/{pid}")
async def delete_product(pid: str, authorized: bool = Depends(verify_admin)):
    data = db.load_data()
    data["products"] = [p for p in data["products"] if p["id"] != pid]
    db.save_data(data)
    return {"status": "success"}

@app.post("/api/admin/category")
async def save_category(category: Category, authorized: bool = Depends(verify_admin)):
    data = db.load_data()
    existing = next((i for i, c in enumerate(data["categories"]) if c["id"] == category.id), None)
    
    cat_dict = category.dict()
    if existing is not None:
        data["categories"][existing] = cat_dict
    else:
        data["categories"].append(cat_dict)
    
    db.save_data(data)
    return {"status": "success"}

@app.delete("/api/admin/category/{cid}")
async def delete_category(cid: str, authorized: bool = Depends(verify_admin)):
    data = db.load_data()
    data["categories"] = [c for c in data["categories"] if c["id"] != cid]
    db.save_data(data)
    return {"status": "success"}

@app.post("/api/admin/order-status")
async def update_order_status(payload: Dict[str, str], authorized: bool = Depends(verify_admin)):
    order_id = payload.get("id")
    status = payload.get("status")
    data = db.load_data()
    for order in data["orders"]:
        if order["id"] == order_id:
            order["status"] = status
            db.save_data(data)
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Order not found")

@app.get("/api/admin/backup")
async def download_backup(token: str):
    # Query param token for file download (Header not possible in simple href)
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403)
    return FileResponse(DATA_FILE, filename="backup.json")

@app.post("/api/admin/restore")
async def restore_backup(file: UploadFile = File(...), authorized: bool = Depends(verify_admin)):
    content = await file.read()
    try:
        json_content = json.loads(content)
        if "products" in json_content and "categories" in json_content:
            db.save_data(json_content)
            return {"status": "success"}
    except:
        pass
    raise HTTPException(status_code=400, detail="Invalid backup file")

# --- Order & Payment Flow ---

@app.post("/api/order/create")
async def create_order(request: Request, order_req: OrderRequest):
    data = db.load_data()
    
    # Calculate Total Server Side
    calculated_total = 0
    full_items = []
    
    for item in order_req.items:
        prod = next((p for p in data["products"] if p["id"] == item.id), None)
        if prod:
            final_price = prod["price"] * (1 - prod["discount"] / 100)
            calculated_total += final_price * item.quantity
            full_items.append({
                "id": prod["id"],
                "name": prod["name"],
                "price": final_price,
                "quantity": item.quantity
            })
    
    total_usd = calculated_total * OMR_TO_USD_RATE
    
    # Create Temp Order ID
    order_id = str(int(datetime.now().timestamp() * 1000))
    
    # Create PayPal Payment
    try:
        base_url = str(request.base_url).rstrip('/')
        return_url = f"{base_url}/api/payment/success?oid={order_id}"
        cancel_url = f"{base_url}/api/payment/cancel"
        
        paypal_order = await paypal_service.create_payment(total_usd, return_url, cancel_url)
        approve_link = next(link["href"] for link in paypal_order["links"] if link["rel"] == "approve")
        
        # Save Pending Order
        new_order = {
            "id": order_id,
            "date": datetime.now().isoformat(),
            "customer": order_req.customer.dict(),
            "items": full_items,
            "total_omr": calculated_total,
            "total_usd": total_usd,
            "status": "pending_payment",
            "paid": False,
            "paypal_order_id": paypal_order["id"]
        }
        
        data["orders"].append(new_order)
        db.save_data(data)
        
        return {"approval_url": approve_link}
        
    except Exception as e:
        logger.error(f"Payment Creation Error: {e}")
        raise HTTPException(status_code=500, detail="Payment creation failed")

@app.get("/api/payment/success")
async def payment_success(oid: str, token: str):
    data = db.load_data()
    order_idx = next((i for i, o in enumerate(data["orders"]) if o["id"] == oid), None)
    
    if order_idx is None:
        return RedirectResponse("/?error=order_not_found")
    
    order = data["orders"][order_idx]
    
    try:
        # Capture Payment
        await paypal_service.capture_payment(token)
        
        # Update Order
        order["status"] = "confirmed"
        order["paid"] = True
        data["orders"][order_idx] = order
        db.save_data(data)
        
        # Send Telegram Notification (Try/Except)
        try:
            await telegram_service.send_order(order)
        except Exception as e:
            logger.error(f"Telegram Failed: {e}")
        
        return RedirectResponse(f"/success?oid={oid}")
        
    except Exception as e:
        logger.error(f"Capture Error: {e}")
        return RedirectResponse("/?error=payment_failed")

@app.get("/api/payment/cancel")
async def payment_cancel():
    return RedirectResponse("/?error=payment_cancelled")

@app.get("/api/order/{oid}")
async def get_order_detail(oid: str):
    data = db.load_data()
    order = next((o for o in data["orders"] if o["id"] == oid), None)
    if order:
        return order
    raise HTTPException(status_code=404, detail="Not found")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)