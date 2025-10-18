#match_engine.py 
import json, os, time
from typing import List, Dict, Tuple
from eth_account import Account
from eth_account.messages import encode_defunct
from orderbook import load_book, save_book, add_orders, prune_expired, sort_book
from mm_bot import inject_mm_quotes

# --------- helpers ---------
def to_int(x) -> int:
    if isinstance(x, int):
        return x
    if isinstance(x, str) and x.isdigit():
        return int(x)
    return int(float(x))

def load_incoming_orders(path="/iexec_in/orders.json") -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

def same_pair(buy: dict, sell: dict) -> bool:
    # buy: tokenIn = QUOTE, tokenOut = BASE
    # sell: tokenOut = BASE, tokenIn = QUOTE
    return (buy["tokenIn"].lower() == sell["tokenIn"].lower() and
            buy["tokenOut"].lower() == sell["tokenOut"].lower()) or \
           (buy["tokenIn"].lower() == sell["tokenOut"].lower() and
            buy["tokenOut"].lower() == sell["tokenIn"].lower())

def try_match(book: Dict[str, List[dict]]) -> Tuple[dict, dict, float]:
    """
    Find best crossing buy & sell on same pair.
    Returns (buy, sell, trade_price)
    """
    if not book["buy"] or not book["sell"]:
        raise ValueError("book empty")

    # Ensure sorted
    # buy: highest price first; sell: lowest price first
    for b in book["buy"]:
        for s in book["sell"]:
            if not same_pair(b, s):
                continue
            if float(b["price"]) >= float(s["price"]):
                trade_px = (float(b["price"]) + float(s["price"])) / 2.0
                return b, s, trade_px

    raise ValueError("no crossing quotes")

def build_trade(buy: dict, sell: dict) -> dict:
    """
    Build settlement trade (maker = seller of BASE; taker = buyer of BASE)
    """
    # Here we move the smaller side notional (simple MVP; you can refine partial fills)
    amountA = to_int(sell["amountOut"])  # base from seller -> buyer
    amountB = to_int(buy["amountOut"])   # quote from buyer -> seller

    return {
        "maker": sell["owner"],               # sends tokenA (base)
        "taker": buy["owner"],                # sends tokenB (quote)
        "tokenA": sell["tokenOut"],           # base token (e.g., WETHm)
        "tokenB": buy["tokenOut"],            # quote token (e.g., USDCm)
        "amountA": str(amountA),
        "amountB": str(amountB),
        "nonce": int(time.time()),
        "deadline": int(time.time()) + 600
    }

def sign_trade(trade: dict, privkey_hex: str) -> Tuple[str, str]:
    msg = encode_defunct(text=json.dumps(trade, sort_keys=True))
    signed = Account.sign_message(msg, private_key=privkey_hex)
    return signed.signature.hex(), Account.from_key(privkey_hex).address

# --------- main ---------
def main():
    print("🚀 iDarkPool worker start")

    # ENV
    ENCLAVE_PRIV = os.environ.get("ENCLAVE_PRIV")
    if not ENCLAVE_PRIV:
        raise SystemExit("❌ Missing ENCLAVE_PRIV env var")

    # (Optional) basic config
    BASE_TOKEN  = os.environ.get("BASE_TOKEN",  "0xBaseToken")   # WETHm
    QUOTE_TOKEN = os.environ.get("QUOTE_TOKEN", "0xQuoteToken")  # USDCm
    MM_ADDRESS  = os.environ.get("MM_ADDRESS",  "0x000000000000000000000000000000000000dEaD")
    REF_PRICE   = float(os.environ.get("REF_PRICE", "2000.0"))

    # 1) Load book and incoming orders (plain JSON for MVP)
    book = load_book()
    incoming = load_incoming_orders()
    if incoming:
        add_orders(book, incoming)

    # 2) Housekeeping
    prune_expired(book)

    # 3) Inject MM quotes (free, internal)
    inject_mm_quotes(
        book=book,
        ref_price=REF_PRICE,
        mm_address=MM_ADDRESS,
        base_token=BASE_TOKEN,
        quote_token=QUOTE_TOKEN,
        spread_bps=50,          # 0.50% spread
        size_base=1.0
    )

    # 4) Sort and attempt match
    sort_book(book)
    try:
        buy, sell, trade_px = try_match(book)
    except Exception as e:
        # Persist and exit gracefully (iExec still returns output)
        save_book(book)
        os.makedirs("/iexec_out", exist_ok=True)
        with open("/iexec_out/result.json", "w") as f:
            json.dump({"status": "no_match", "reason": str(e)}, f, indent=2)
        print("ℹ️ No match:", e)
        return

    # 5) Build settlement trade & sign
    trade = build_trade(buy, sell)
    signature, enclave_addr = sign_trade(trade, ENCLAVE_PRIV)

    # 6) Remove matched orders (very naive: remove first occurrence)
    book["buy"].remove(buy)
    book["sell"].remove(sell)
    save_book(book)

    # 7) Write result
    os.makedirs("/iexec_out", exist_ok=True)
    result = {
        "status": "matched",
        "price": trade_px,
        "trade": trade,
        "signature": signature,
        "enclave": enclave_addr
    }
    with open("/iexec_out/result.json", "w") as f:
        json.dump(result, f, indent=2)

    print("✅ Match written to /iexec_out/result.json")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
