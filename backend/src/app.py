import os, json
from orderbook import load_book, save_book, add_orders, prune_expired, sort_book, export_orderbook
from match_engine import build_trade, sign_trade, try_match
from mm_bot import inject_mm_quotes

# -------------------------------------------------
# 1️⃣  Environment
# -------------------------------------------------
ENCLAVE_PRIV = os.getenv("ENCLAVE_PRIV")
BASE_TOKEN = os.getenv("BASE_TOKEN", "0xWETHm")
QUOTE_TOKEN = os.getenv("QUOTE_TOKEN", "0xUSDCm")
MM_ADDRESS = os.getenv("MM_ADDRESS", "0x000000000000000000000000000000000000dEaD")
REF_PRICE = float(os.getenv("REF_PRICE", "2000.0"))

IEXEC_IN = os.getenv("IEXEC_IN", "./iexec_in")
IEXEC_OUT = os.getenv("IEXEC_OUT", "./iexec_out")
os.makedirs(IEXEC_OUT, exist_ok=True)

ORDERS_PATH = os.path.join(IEXEC_IN, "orders.json")
RESULT_PATH = os.path.join(IEXEC_OUT, "result.json")

# -------------------------------------------------
# 2️⃣  Main Worker Logic
# -------------------------------------------------
def main():
    print("🚀 iDarkPool Worker starting...")

    if not ENCLAVE_PRIV:
        raise SystemExit("❌ ENCLAVE_PRIV not set")

    # --- Load or init orderbook ---
    book = load_book()

    export_orderbook()
    # --- Inject Market Maker quotes ---
    inject_mm_quotes(
        book=book,
        ref_price=REF_PRICE,
        mm_address=MM_ADDRESS,
        base_token=BASE_TOKEN,
        quote_token=QUOTE_TOKEN,
        spread_bps=50,   # 0.5% spread
        size_base=1.0,
    )

    # --- Load user orders (if any) ---
    if os.path.exists(ORDERS_PATH):
        with open(ORDERS_PATH) as f:
            orders = json.load(f)
            print(f"📥 Loaded {len(orders)} user orders.")
            add_orders(book, orders)

    # --- Clean + sort ---
    prune_expired(book)
    sort_book(book)

    # --- Attempt match ---
    try:
        buy, sell, price = try_match(book)
    except Exception as e:
        print(f"ℹ️ No match found: {e}")
        save_book(book)
        result = {"status": "no_match", "reason": str(e)}
        with open(RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)
        print("✅ Result written: no match.")
        return

    print(f"✅ Match found! Price {price}")
    trade = build_trade(buy, sell)
    sig, enclave = sign_trade(trade, ENCLAVE_PRIV)

    # Remove executed orders
    if buy in book["buy"]:
        book["buy"].remove(buy)
    if sell in book["sell"]:
        book["sell"].remove(sell)
    save_book(book)

    result = {
        "status": "matched",
        "price": price,
        "trade": trade,
        "signature": sig,
        "enclave": enclave,
    }
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print("✅ Match written to /iexec_out/result.json")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    print("🚀 iDarkPool Worker starting...")

    main()

    export_orderbook()