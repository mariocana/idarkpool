# SPDX-License-Identifier: MIT
# iDarkPool – Market Maker Injector v2
# Mario Canalella – 2025

from typing import Dict


def inject_mm_quotes(
    book: Dict[str, list],
    ref_price: float,
    mm_address: str,
    base_token: str,      # e.g. WETHm
    quote_token: str,     # e.g. USDCm
    levels: int = 3,      # number of bid/ask levels
    spread_bps: float = 50,  # 0.50% base spread
    step_bps: float = 25,    # additional spread per level
    size_base: float = 1.0,
    base_decimals: int = 18,
    quote_decimals: int = 18,
    ensure_cross: bool = True,  # guarantee at least one crossing quote
):
    """
    Injects a layered market maker book around a reference price.

    - Produces limit BUY (bids) and SELL (asks)
    - Each level widens spread gradually
    - Optionally ensures one crossing bid for demo testing
    """

    book.setdefault("buy", [])
    book.setdefault("sell", [])

    for i in range(levels):
        # widen spread each level
        spread = (spread_bps + i * step_bps) / 10_000
        bid_px = ref_price * (1 - spread)
        ask_px = ref_price * (1 + spread)

        # SELL base (ask) — MM provides base_token and wants quote_token
        ask = {
            "owner": mm_address,
            "side": "sell",
            "orderType": "limit",
            "tokenOut": base_token,
            "tokenIn": quote_token,
            "amountOut": str(int(size_base * (10 ** base_decimals))),
            "amountIn": str(int(ref_price * size_base * (10 ** quote_decimals))),
            "price": round(ask_px, 2),
            "deadline": 9999999999,
        }

        # BUY base (bid) — MM provides quote_token and wants base_token
        bid = {
            "owner": mm_address,
            "side": "buy",
            "orderType": "limit",
            "tokenOut": quote_token,
            "tokenIn": base_token,
            "amountOut": str(int(ref_price * size_base * (10 ** quote_decimals))),
            "amountIn": str(int(size_base * (10 ** base_decimals))),
            "price": round(bid_px, 2),
            "deadline": 9999999999,
        }

        book["buy"].append(bid)
        book["sell"].append(ask)

    if ensure_cross:
        book["buy"].append({
            "owner": mm_address,
            "side": "buy",
            "orderType": "limit",
            "tokenOut": quote_token,
            "tokenIn": base_token,
            "amountOut": str(int(ref_price * size_base * (10 ** quote_decimals))),
            "amountIn": str(int(size_base * (10 ** base_decimals))),
            "price": round(ref_price * 1.01, 2),  # intentionally 1% above mid
            "deadline": 9999999999,
        })

    print(f"📘 Injected {len(book['buy'])} bids / {len(book['sell'])} asks into book")