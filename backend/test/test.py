import json
import os
import time
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode as abi_encode

# -------------------------------------------------
# 1️⃣  Load configuration
# -------------------------------------------------
load_dotenv()

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("ENCLAVE_PRIV")
CHAIN_ID = int(os.getenv("CHAIN_ID", 31337))
SETTLEMENT_ADDR = os.getenv("SETTLEMENT_ADDR")
WETHM_ADDR = os.getenv("WETHM_ADDR")
USDCM_ADDR = os.getenv("USDCM_ADDR")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)

print("🔑 Enclave (worker) address:", account.address)
print("📡 RPC:", RPC_URL)

# -------------------------------------------------
# 2️⃣  Load ABIs
# -------------------------------------------------
def load_abi(name):
    with open(f"abi/{name}.json") as f:
        data = json.load(f)
        # Handle both full Foundry artifact or pure ABI list
        if isinstance(data, dict) and "abi" in data:
            return data["abi"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"Unexpected ABI format in {name}.json")

weth_abi = load_abi("WETHm")
usdc_abi = load_abi("USDCm")
settlement_abi = load_abi("DarkPoolSettlement")

weth = w3.eth.contract(address=Web3.to_checksum_address(WETHM_ADDR), abi=weth_abi)
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDCM_ADDR), abi=usdc_abi)
settlement = w3.eth.contract(address=Web3.to_checksum_address(SETTLEMENT_ADDR), abi=settlement_abi)

# -------------------------------------------------
# 3️⃣  Mint & Approve mock tokens (for local test)
# -------------------------------------------------
def send_tx(tx):
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash.hex(), receipt.status

def mint_and_approve():
    print("🪙 Minting tokens...")
    nonce = w3.eth.get_transaction_count(account.address)
    tx1 = weth.functions.mint(account.address, Web3.to_wei(10, 'ether')).build_transaction({
        'from': account.address, 'nonce': nonce, 'gas': 400000, 'gasPrice': w3.to_wei('1', 'gwei')
    })
    send_tx(tx1)
    tx2 = usdc.functions.mint(account.address, Web3.to_wei(20000, 'ether')).build_transaction({
        'from': account.address, 'nonce': nonce+1, 'gas': 400000, 'gasPrice': w3.to_wei('1', 'gwei')
    })
    send_tx(tx2)

    print("✅ Approving settlement...")
    for i, token in enumerate([weth, usdc]):
        tx = token.functions.approve(SETTLEMENT_ADDR, Web3.to_wei(10000, 'ether')).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 300000,
            'gasPrice': w3.to_wei('1', 'gwei'),
        })
        send_tx(tx)
    print("✅ Tokens ready.")

# -------------------------------------------------
# 4️⃣  Build + Sign trade
# -------------------------------------------------
def build_trade():
    trade = {
        "maker": account.address,
        "taker": account.address,  # for local test
        "tokenA": USDCM_ADDR,
        "tokenB": WETHM_ADDR,
        "amountA": Web3.to_wei(2000, 'ether'),
        "amountB": Web3.to_wei(1, 'ether'),
        "nonce": 1,
        "deadline": int(time.time()) + 600
    }

    payload = abi_encode(
        ["address","address","address","address","uint256","uint256","uint256","uint256"],
        [trade[k] for k in ["maker","taker","tokenA","tokenB","amountA","amountB","nonce","deadline"]]
    )
    trade_hash = Web3.keccak(payload)          # matches abi.encode in Solidity
    message = encode_defunct(primitive=trade_hash)
    signed = Account.sign_message(message, private_key=PRIVATE_KEY)
    print("🧾 Trade hash:", trade_hash.hex())
    print("🖋 Signature:", signed.signature.hex())
    
    recovered = Account.recover_message(message, signature=signed.signature)
    print("🔎 Recovered:", recovered)
    print("🔐 Enclave  :", account.address)  # must match


    return trade, signed.signature

# -------------------------------------------------
# 5️⃣  Call settle()
# -------------------------------------------------
def settle_trade(trade, signature):
    if isinstance(signature, bytes):
        signature = signature.hex()  # convert bytes to hex string

    sig_bytes = bytes.fromhex(signature[2:]) if signature.startswith("0x") else bytes.fromhex(signature)
    tx = settlement.functions.settle(
        (
            trade["maker"],
            trade["taker"],
            trade["tokenA"],
            trade["tokenB"],
            trade["amountA"],
            trade["amountB"],
            trade["nonce"],
            trade["deadline"]
        ),
        sig_bytes
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 1_000_000,
        "gasPrice": w3.to_wei("1", "gwei"),
        "chainId": CHAIN_ID,
    })

    print("🚀 Sending settle() transaction...")
    tx_hash, status = send_tx(tx)
    print("✅ Transaction hash:", tx_hash)
    print("✅ Status:", "SUCCESS" if status == 1 else "FAILED")

# -------------------------------------------------
# 6️⃣  Check balances
# -------------------------------------------------
def show_balances():
    bal_weth = weth.functions.balanceOf(account.address).call()
    bal_usdc = usdc.functions.balanceOf(account.address).call()
    print("💰 Balances:")
    print("   WETHm:", w3.from_wei(bal_weth, 'ether'))
    print("   USDCm:", w3.from_wei(bal_usdc, 'ether'))

# -------------------------------------------------
# 7️⃣  Main
# -------------------------------------------------
if __name__ == "__main__":
    print("\n=== iDarkPool Local Worker (no API) ===")
    mint_and_approve()
    trade, sig = build_trade()
    settle_trade(trade, sig)
    show_balances()