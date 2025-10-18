# SPDX-License-Identifier: MIT
# iDarkPool Two-Party Settlement Test – Mario Canalella 2025
# Version v2.1 (with balance logging)

import os, time, json
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode as abi_encode

# -------------------------------------------------
# 1️⃣  Load config
# -------------------------------------------------
load_dotenv()
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")              # enclave signer key
CHAIN_ID = int(os.getenv("CHAIN_ID", 31337))
SETTLEMENT_ADDR = os.getenv("SETTLEMENT_ADDR")
WETHM_ADDR = os.getenv("WETHM_ADDR")
USDCM_ADDR = os.getenv("USDCM_ADDR")

# second local account from Anvil (index 1)
TAKER_PRIV = os.getenv("TAKER_PRIV")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
enclave = Account.from_key(PRIVATE_KEY)
taker = Account.from_key(TAKER_PRIV)

print("🔑 Enclave (signer):", enclave.address)
print("👤 Maker:", enclave.address)
print("👤 Taker:", taker.address)
print("📡 RPC:", RPC_URL)

# -------------------------------------------------
# 2️⃣  Load ABIs
# -------------------------------------------------
def load_abi(name):
    with open(f"abi/{name}.json") as f:
        data = json.load(f)
        if isinstance(data, dict) and "abi" in data:
            return data["abi"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"Invalid ABI in {name}.json")

weth_abi = load_abi("WETHm")
usdc_abi = load_abi("USDCm")
settlement_abi = load_abi("DarkPoolSettlement")

weth = w3.eth.contract(address=Web3.to_checksum_address(WETHM_ADDR), abi=weth_abi)
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDCM_ADDR), abi=usdc_abi)
settlement = w3.eth.contract(address=Web3.to_checksum_address(SETTLEMENT_ADDR), abi=settlement_abi)

# -------------------------------------------------
# 3️⃣  Helpers
# -------------------------------------------------
def send_tx(tx, key=None):
    from_addr = tx["from"]
    tx["nonce"] = w3.eth.get_transaction_count(from_addr, "pending")

    # ✅ use EIP-1559 compatible fee fields
    base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
    tx["maxFeePerGas"] = base_fee + w3.to_wei(2, "gwei")
    tx["maxPriorityFeePerGas"] = w3.to_wei(1, "gwei")

    # remove legacy gasPrice
    tx.pop("gasPrice", None)

    signed = w3.eth.account.sign_transaction(tx, key or PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    print(f"✅ {tx_hash.hex()} mined in block {receipt.blockNumber}")
    return receipt

def fmt(v):  # clean decimal formatting
    return round(w3.from_wei(v, "ether"), 4)

def get_balances():
    return {
        "maker": {
            "WETHm": weth.functions.balanceOf(enclave.address).call(),
            "USDCm": usdc.functions.balanceOf(enclave.address).call(),
        },
        "taker": {
            "WETHm": weth.functions.balanceOf(taker.address).call(),
            "USDCm": usdc.functions.balanceOf(taker.address).call(),
        }
    }

def print_balances(bal, title="Balances"):
    print(f"\n📊 {title}")
    print(f"   Maker →  WETHm: {fmt(bal['maker']['WETHm'])} | USDCm: {fmt(bal['maker']['USDCm'])}")
    print(f"   Taker →  WETHm: {fmt(bal['taker']['WETHm'])} | USDCm: {fmt(bal['taker']['USDCm'])}")

# -------------------------------------------------
# -------------------------------------------------
# 4️⃣  Mint and Approve
# -------------------------------------------------
def mint_and_approve():
    print("🪙 Minting + approving tokens for both parties...")

    # --------------- MINTING ---------------
    # Maker (enclave) gets both WETHm and USDCm
    send_tx(
        weth.functions.mint(enclave.address, Web3.to_wei(20, 'ether')).build_transaction({
            'from': enclave.address,
            'nonce': w3.eth.get_transaction_count(enclave.address, 'pending'),
            'gas': 300000,
            'gasPrice': 0,
        }),
        PRIVATE_KEY,
    )
    send_tx(
        usdc.functions.mint(enclave.address, Web3.to_wei(20000, 'ether')).build_transaction({
            'from': enclave.address,
            'nonce': w3.eth.get_transaction_count(enclave.address, 'pending'),
            'gas': 300000,
            'gasPrice': 0,
        }),
        PRIVATE_KEY,
    )

    # Taker gets some WETHm and USDCm
    send_tx(
        weth.functions.mint(taker.address, Web3.to_wei(5, 'ether')).build_transaction({
            'from': enclave.address,
            'nonce': w3.eth.get_transaction_count(enclave.address, 'pending'),
            'gas': 300000,
            'gasPrice': 0,
        }),
        PRIVATE_KEY,
    )
    send_tx(
        usdc.functions.mint(taker.address, Web3.to_wei(40000, 'ether')).build_transaction({
            'from': enclave.address,
            'nonce': w3.eth.get_transaction_count(enclave.address, 'pending'),
            'gas': 300000,
            'gasPrice': 0,
        }),
        PRIVATE_KEY,
    )

    # --------------- LOG BALANCES ---------------
    maker_weth = fmt(weth.functions.balanceOf(enclave.address).call())
    maker_usdc = fmt(usdc.functions.balanceOf(enclave.address).call())
    taker_weth = fmt(weth.functions.balanceOf(taker.address).call())
    taker_usdc = fmt(usdc.functions.balanceOf(taker.address).call())

    print(f"👀 Maker → WETH: {maker_weth} | USDC: {maker_usdc}")
    print(f"👀 Taker → WETH: {taker_weth} | USDC: {taker_usdc}")

    # --------------- APPROVALS ---------------
    # Maker approves USDCm (they’re selling USDC)
    send_tx(
        usdc.functions.approve(SETTLEMENT_ADDR, Web3.to_wei(10000, 'ether')).build_transaction({
            'from': enclave.address,
            'nonce': w3.eth.get_transaction_count(enclave.address, 'pending'),
            'gas': 200000,
            'gasPrice': 0,
        }),
        PRIVATE_KEY,
    )

    # Taker approves WETHm (they’re selling WETH)
    send_tx(
        weth.functions.approve(SETTLEMENT_ADDR, Web3.to_wei(10000, 'ether')).build_transaction({
            'from': taker.address,
            'nonce': w3.eth.get_transaction_count(taker.address, 'pending'),
            'gas': 200000,
            'gasPrice': 0,
        }),
        TAKER_PRIV,
    )

    print("✅ Approvals complete.")

# -------------------------------------------------
# 5️⃣  Build and sign trade
# -------------------------------------------------
def build_and_sign():
    trade = {
        "maker": enclave.address,
        "taker": taker.address,
        "tokenA": Web3.to_checksum_address(USDCM_ADDR),
        "tokenB": Web3.to_checksum_address(WETHM_ADDR),
        "amountA": Web3.to_wei(2000, 'ether'),
        "amountB": Web3.to_wei(1, 'ether'),
        "nonce": 2,
        "deadline": int(time.time()) + 600,
    }

    # ✅ Match Solidity: keccak256(abi.encode(...))
    encoded = abi_encode(
        ['address','address','address','address','uint256','uint256','uint256','uint256'],
        [
            trade["maker"],
            trade["taker"],
            trade["tokenA"],
            trade["tokenB"],
            trade["amountA"],
            trade["amountB"],
            trade["nonce"],
            trade["deadline"],
        ]
    )
    trade_hash = Web3.keccak(encoded)
    print("🧾 Trade hash:", trade_hash.hex())

    # Ethereum Signed Message prefix (exactly like contract)
    eth_signed = Web3.keccak(b"\x19Ethereum Signed Message:\n32" + trade_hash)

    # Sign and verify (works on older eth-account too)
    signed = Account._sign_hash(eth_signed, private_key=PRIVATE_KEY)
    print("🖋 Signature:", signed.signature.hex())

    try:
        recovered = Account.recover_hash(eth_signed, signature=signed.signature)
    except AttributeError:
        recovered = Account._recover_hash(eth_signed, signature=signed.signature)

    contract_signer = settlement.functions.enclaveSigner().call()
    print("🔎 Recovered (Python):", recovered)
    print("🔐 EnclaveSigner (Solidity):", contract_signer)
    print("✅ Signature matches:", recovered.lower() == contract_signer.lower())

    return trade, signed.signature

# -------------------------------------------------
# 6️⃣  Call settle()
# -------------------------------------------------
def settle_trade(trade, sig):
    # Normalize signature to hex string if it's bytes
    if isinstance(sig, bytes):
        sig = sig.hex()

    # Ensure starts with 0x prefix
    if not sig.startswith("0x"):
        sig = "0x" + sig

    # Convert to bytes
    sig_bytes = bytes.fromhex(sig[2:])
    tx = settlement.functions.settle(
        (
            trade["maker"], trade["taker"], trade["tokenA"], trade["tokenB"],
            trade["amountA"], trade["amountB"], trade["nonce"], trade["deadline"]
        ),
        sig_bytes
    ).build_transaction({
        'from': taker.address,
        'nonce': w3.eth.get_transaction_count(taker.address),
        'gas': 800000,
        'gasPrice': w3.to_wei('1', 'gwei'),
        'chainId': CHAIN_ID,
    })
    print("🔏 Sig length:", len(sig_bytes))
    print("🔏 First 4 bytes:", sig_bytes[:4].hex())
    print("\n🚀 Submitting settle() from taker...")
    receipt = send_tx(tx, TAKER_PRIV)
    print("✅ Tx hash:", receipt.transactionHash.hex())
    print("✅ Status:", "SUCCESS" if receipt.status == 1 else "FAILED")

# -------------------------------------------------
# 7️⃣  Run
# -------------------------------------------------
if __name__ == "__main__":
    print("\n=== iDarkPool Two-Party Local Test ===")
    mint_and_approve()

    initial_bal = get_balances()
    print_balances(initial_bal, "Initial Balances")

    trade, sig = build_and_sign()
    settle_trade(trade, sig)

    final_bal = get_balances()
    print_balances(final_bal, "Final Balances")

    print("\n📈 Δ Change:")
    for actor in ["maker", "taker"]:
        dw_wei = int(final_bal[actor]["WETHm"]) - int(initial_bal[actor]["WETHm"])
        du_wei = int(final_bal[actor]["USDCm"]) - int(initial_bal[actor]["USDCm"])
        dw = round(dw_wei / 1e18, 4)
        du = round(du_wei / 1e18, 4)
        print(f"   {actor.capitalize()} Δ WETHm: {dw:+}, USDCm: {du:+}")
