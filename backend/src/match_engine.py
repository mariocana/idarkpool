import json, os, time
from typing import List, Tuple
from eth_account import Account
from eth_account.messages import encode_defunct

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

def try_match(book):
    if not book["buy"] or not book["sell"]:
        raise ValueError("book empty")

    for b in book["buy"]:
        for s in book["sell"]:
            if not same_pair(b, s):
                continue

            # MARKET BUY — immediately execute at best available sell price
            if b.get("orderType") == "market":
                trade_px = float(s["price"])
                return b, s, trade_px

            # MARKET SELL — immediately execute at best available buy price
            if s.get("orderType") == "market":
                trade_px = float(b["price"])
                return b, s, trade_px

            # LIMIT vs LIMIT — cross check
            if float(b["price"]) >= float(s["price"]):
                trade_px = (float(b["price"]) + float(s["price"])) / 2
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