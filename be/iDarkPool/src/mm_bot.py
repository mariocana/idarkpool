from typing import Dict

def inject_mm_quotes(
    book: Dict[str, list],
    ref_price: float,
    mm_address: str,
    base_token: str,  # e.g., WETHm
    quote_token: str, # e.g., USDCm
    spread_bps: int = 50,  # 0.50%
    size_base: float = 1.0,
    quote_decimals: int = 18,
    base_decimals: int = 18,
):
    """
    Adds two standing quotes around ref_price:
      - bid:  ref*(1 - spread)
      - ask:  ref*(1 + spread)
    """
    spread = spread_bps / 10_000
    bid_px = ref_price * (1 - spread)
    ask_px = ref_price * (1 + spread)

    # SELL base for quote (ask): maker sells base_token, receives quote_token
    ask = {
        "owner": mm_address,
        "side": "sell",
        "tokenOut": base_token,
        "tokenIn": quote_token,
        "amountOut": str(int(size_base * (10**base_decimals))),
        "amountIn":  str(int(ref_price * size_base * (10**quote_decimals))),
        "price": ask_px,
        "deadline": 9999999999
    }

    # BUY base with quote (bid): maker buys base_token, pays quote_token
    # We represent a bid as a BUY order from the MM’s POV (will match with a user SELL)
    bid = {
        "owner": mm_address,
        "side": "buy",
        "tokenOut": quote_token,
        "tokenIn":  base_token,
        "amountOut": str(int(ref_price * size_base * (10**quote_decimals))),
        "amountIn":  str(int(size_base * (10**base_decimals))),
        "price": bid_px,
        "deadline": 9999999999
    }

    book["buy"].append(bid)
    book["sell"].append(ask)