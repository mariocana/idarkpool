import json
import os
import time
from typing import Dict, List

BOOK_PATH = "/iexec_in/orderbook.json"

def _empty() -> Dict[str, List[dict]]:
    return {"buy": [], "sell": []}

def load_book() -> Dict[str, List[dict]]:
    if os.path.exists(BOOK_PATH):
        with open(BOOK_PATH) as f:
            try:
                return json.load(f)
            except Exception:
                return _empty()
    return _empty()

def save_book(book: Dict[str, List[dict]]) -> None:
    os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=2)

def add_orders(book: Dict[str, List[dict]], incoming: List[dict]) -> None:
    now = int(time.time())
    for o in incoming:
        side = o["side"].lower()
        assert side in ("buy", "sell"), "order.side must be buy|sell"
        o.setdefault("ts", now)
        book[side].append(o)

def prune_expired(book: Dict[str, List[dict]]) -> None:
    now = int(time.time())
    for side in ("buy", "sell"):
        book[side] = [o for o in book[side] if o.get("deadline", now+1) >= now]

def sort_book(book: Dict[str, List[dict]]) -> None:
    # Highest bid first; lowest ask first
    book["buy"].sort(key=lambda x: (float(x["price"]), -x.get("ts", 0)), reverse=True)
    book["sell"].sort(key=lambda x: (float(x["price"]), x.get("ts", 0)))

def export_orderbook():
    """Save the current orderbook to /iexec_out/orderbook.json"""
    book = load_book()
    prune_expired(book)
    sort_book(book)

    os.makedirs("/iexec_out", exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=2)
    print(f"📘 Orderbook exported to {BOOK_PATH}")
