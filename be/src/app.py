# SPDX-License-Identifier: MIT
# iDarkPool Worker REST – Full On-chain Settlement Integration
# Author: Mario Canalella (2025)

import os
import json
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

from orderbook import load_book, save_book, add_orders, prune_expired, sort_book
from mm_bot import inject_mm_quotes
from match_engine import build_trade, sign_trade, try_match

# -------------------------------------------------
# ⚙️ CONFIGURATION
# -------------------------------------------------
app = FastAPI(title="iDarkPool REST Worker")

DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)
ORDERS_PATH = os.path.join(DATA_DIR, "orders.json")
RESULT_PATH = os.path.join(DATA_DIR, "result.json")

# Environment setup
ENCLAVE_PRIV = os.getenv("ENCLAVE_PRIV")
PRIVATE_KEY = ENCLAVE_PRIV  # same in this MVP
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("CHAIN_ID", 31337))
SETTLEMENT_ADDR = os.getenv("SETTLEMENT_ADDR")
BASE_TOKEN = os.getenv("BASE_TOKEN", "0xBaseToken")
QUOTE_TOKEN = os.getenv("QUOTE_TOKEN", "0xQuoteToken")
MM_ADDRESS = os.getenv("MM_ADDRESS", "0x000000000000000000000000000000000000dEaD")
REF_PRICE = float(os.getenv("REF_PRICE", "2000.0"))

# Web3 setup
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)
print(f"🔑 Enclave signer: {account.address}")
print(f"📡 RPC connected: {RPC_URL}")

# Load contract ABI
with open("abi/DarkPoolSettlement.json") as f:
    data = json.load(f)
settlement_abi = data["abi"] if "abi" in data else data
settlement = w3.eth.contract(
    address=Web3.to_checksum_address(SETTLEMENT_ADDR),
    abi=settlement_abi,
)

# -------------------------------------------------
# 🧱 MODELS
# -------------------------------------------------
class Order(BaseModel):
    owner: str
    side: str
    tokenIn: str
    tokenOut: str
    amountIn: str
    amountOut: str
    price: float
    deadline: int = int(time.time()) + 600

# -------------------------------------------------
# ⚙️ UTILS
# -------------------------------------------------
def send_tx(tx):
    """Sign + send a transaction and wait for confirmation."""
    base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
    tx["maxFeePerGas"] = base_fee + w3.to_wei(2, "gwei")
    tx["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")
    tx.pop("gasPrice", None)

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    print(f"✅ Tx {tx_hash.hex()} mined in block {receipt.blockNumber} | status: {receipt.status}")
    return tx_hash.hex(), receipt.status

# -------------------------------------------------
# 🚀 ROUTES
# -------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "iDarkPool REST Worker running"}

@app.post("/orders")
def submit_order(order: Order):
    """Add a limit order (buy/sell)."""
    book = load_book()
    add_orders(book, [order.dict()])
    save_book(book)

    # Save also separately for record
    with open(ORDERS_PATH, "w") as f:
        json.dump([order.dict()], f, indent=2)

    print(f"📥 New {order.side.upper()} order added @ price {order.price}")
    return {"status": "added", "order": order.dict()}

@app.get("/orderbook")
def get_book():
    """Return current state of the order book."""
    book = load_book()
    prune_expired(book)
    sort_book(book)
    return book

@app.post("/match")
def run_match():
    """Match orders, sign trade, and call on-chain settle()."""
    if not ENCLAVE_PRIV:
        raise HTTPException(500, "ENCLAVE_PRIV not set")

    book = load_book()
    prune_expired(book)
    sort_book(book)

    # Inject MM orders to simulate market depth
    inject_mm_quotes(book, REF_PRICE, MM_ADDRESS, BASE_TOKEN, QUOTE_TOKEN, spread_bps=50)
    save_book(book)

    try:
        buy, sell, trade_px = try_match(book)
    except Exception as e:
        print(f"⚠️ No match found: {e}")
        return {"status": "no_match", "error": str(e)}

    trade = build_trade(buy, sell)
    sig, enclave = sign_trade(trade, ENCLAVE_PRIV)
    print("🧾 Trade:", json.dumps(trade, indent=2))
    print(f"🖋 Signature: {sig[:10]}...")

    # =========== 🔗 On-chain Settlement ===========
    sig_bytes = bytes.fromhex(sig[2:] if sig.startswith("0x") else sig)
    tx = settlement.functions.settle(
        (
            trade["maker"],
            trade["taker"],
            trade["tokenA"],
            trade["tokenB"],
            int(trade["amountA"]),
            int(trade["amountB"]),
            int(trade["nonce"]),
            int(trade["deadline"]),
        ),
        sig_bytes
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "gas": 1_000_000,
        "gasPrice": w3.to_wei("1", "gwei"),
        "chainId": CHAIN_ID,
    })

    tx_hash, status = send_tx(tx)

    # Remove matched from book
    book["buy"].remove(buy)
    book["sell"].remove(sell)
    save_book(book)

    result = {
        "status": "matched" if status == 1 else "failed",
        "price": trade_px,
        "trade": trade,
        "signature": sig,
        "tx_hash": tx_hash,
        "enclave": enclave,
    }

    with open(RESULT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    return result

@app.get("/trade/latest")
def latest_trade():
    if not os.path.exists(RESULT_PATH):
        raise HTTPException(404, "No trades yet")
    with open(RESULT_PATH) as f:
        return json.load(f)

# -------------------------------------------------
# 🏁 MAIN
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting iDarkPool Worker REST server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
