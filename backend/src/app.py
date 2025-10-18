# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, json, time

# --- Internal imports ---
from orderbook import load_book, save_book, add_orders, prune_expired, sort_book
from match_engine import build_trade, sign_trade, try_match
from mm_bot import inject_mm_quotes

app = FastAPI(title="iDarkPool Worker API")

# Environment config
DATA_DIR = os.getenv("DATA_DIR", "./data")
ORDERS_PATH = os.path.join(DATA_DIR, "orders.json")
RESULT_PATH = os.path.join(DATA_DIR, "result.json")
ENCLAVE_PRIV = os.getenv("ENCLAVE_PRIV")

BASE_TOKEN = os.getenv("BASE_TOKEN", "0xWETHm")
QUOTE_TOKEN = os.getenv("QUOTE_TOKEN", "0xUSDCm")
MM_ADDRESS = os.getenv("MM_ADDRESS", "0xMarketMaker")
REF_PRICE = float(os.getenv("REF_PRICE", "2000.0"))


# ---------------- MODELS ----------------
class Order(BaseModel):
    owner: str
    side: str                 # "buy" or "sell"
    tokenIn: str
    tokenOut: str
    amount: float
    price: float
    deadline: int = int(time.time()) + 600

class Trade(BaseModel):
    maker: str
    taker: str
    tokenA: str
    tokenB: str
    amountA: str
    amountB: str
    nonce: int
    deadline: int

# ------------------ STARTUP ------------------

@app.on_event("startup")
def bootstrap_market():
    """Run once at startup: inject market-maker quotes."""
    print("🚀 Bootstrapping orderbook with MM quotes...")
    book = load_book()
    prune_expired(book)
    sort_book(book)

    inject_mm_quotes(
        book=book,
        ref_price=REF_PRICE,
        mm_address=MM_ADDRESS,
        base_token=BASE_TOKEN,
        quote_token=QUOTE_TOKEN,
        spread_bps=50,  # ±0.5% spread
        size_base=1.0
    )
    save_book(book)
    print(f"✅ MM book initialized at ref {REF_PRICE}")


# ---------------- ROUTES ----------------

@app.get("/")
def root():
    return {"status": "ok", "message": "iDarkPool worker REST API running"}


@app.post("/orders")
def submit_order(order: Order):
    """Accept new orders and update the local book."""
    book = load_book()
    add_orders(book, [order.dict()])
    save_book(book)

    with open(ORDERS_PATH, "w") as f:
        json.dump([order.dict()], f, indent=2)

    return {"status": "added", "order": order.dict()}


@app.get("/orderbook")
def get_orderbook():
    """View current buy/sell book (after pruning and sorting)."""
    book = load_book()
    prune_expired(book)
    sort_book(book)
    return book


@app.post("/match")
def run_match():
    """Run the matching engine — find best bid/ask, sign trade."""
    if not ENCLAVE_PRIV:
        raise HTTPException(500, "ENCLAVE_PRIV not set")

    book = load_book()
    prune_expired(book)
    sort_book(book)

    # Inject synthetic liquidity
    inject_mm_quotes(book, REF_PRICE, MM_ADDRESS, BASE_TOKEN, QUOTE_TOKEN, spread_bps=50)
    save_book(book)

    # Try to match any orders
    try:
        buy, sell, trade_px = try_match(book)
    except Exception as e:
        return {"status": "no_match", "error": str(e)}

    # Build and sign a settlement trade
    trade = build_trade(buy, sell)
    sig, enclave = sign_trade(trade, ENCLAVE_PRIV)

    # Remove matched orders from book
    book["buy"].remove(buy)
    book["sell"].remove(sell)
    save_book(book)

    result = {
        "status": "matched",
        "price": trade_px,
        "trade": trade,
        "signature": sig,
        "enclave": enclave,
    }
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    return result


@app.get("/trade/latest")
def latest_trade():
    """Return latest trade result (if any)."""
    if not os.path.exists(RESULT_PATH):
        raise HTTPException(404, "No trades yet")
    with open(RESULT_PATH) as f:
        return json.load(f)
