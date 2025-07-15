import os
import time
import secrets
import string
import random
import sys
from web3 import Web3
from dotenv import load_dotenv

# === Setup ===
load_dotenv()

RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x51be1ef20a1fd5179419738fc71d95a8b6f8a175")
ACCOUNTS_FILE = "accounts.txt"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print(f"❌ Gagal konek ke RPC: {RPC_URL}")
    sys.exit(1)
else:
    print(f"✅ Terkoneksi ke Pharos RPC")

# === ABI ===
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "commitment", "type": "bytes32"}],
        "name": "commit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "bytes32", "name": "secret", "type": "bytes32"},
            {"internalType": "uint256", "name": "duration", "type": "uint256"}
        ],
        "name": "register",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"}
        ],
        "name": "available",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "name", "type": "string"},
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "bytes32", "name": "secret", "type": "bytes32"}
        ],
        "name": "makeCommitment",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function"
    }
]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# === Wallet Loader ===
def load_wallets(path):
    try:
        with open(path) as f:
            return [{'private_key': k.strip(), 'address': w3.eth.account.from_key(k.strip()).address}
                    for k in f if k.strip()]
    except Exception as e:
        print(f"❌ Gagal baca file akun: {e}")
        return []

wallets = load_wallets(ACCOUNTS_FILE)
if not wallets:
    print("❌ Tidak ada wallet ditemukan.")
    sys.exit(1)

print(f"🔑 Loaded {len(wallets)} wallet")

# === Helper ===
def random_domain(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def domain_available(name):
    try:
        return contract.functions.available(name).call()
    except Exception as e:
        print(f"❌ Gagal cek domain {name}: {e}")
        return False

def get_gas_price():
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(1, 'gwei')

def sign_and_send(txn, pk):
    try:
        signed = w3.eth.account.sign_transaction(txn, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        status = "✅" if receipt.status == 1 else "❌"
        print(f"{status} Tx hash: {tx_hash.hex()}")
        return receipt.status == 1
    except Exception as e:
        print(f"❌ Tx error: {e}")
        return False

# === Mint Domain ===
def register_domain(domain, wallet):
    addr = wallet['address']
    pk = wallet['private_key']
    print(f"\n🚀 Coba mint domain: {domain}.phrs untuk {addr}")

    if not domain_available(domain):
        print(f"⚠️ Domain {domain}.phrs sudah diambil, skip...")
        return

    secret = secrets.token_bytes(32)
    nonce = w3.eth.get_transaction_count(addr)
    gas = get_gas_price()

    try:
        commitment = contract.functions.makeCommitment(domain, addr, secret).call()
        commit_tx = contract.functions.commit(commitment).build_transaction({
            'from': addr, 'nonce': nonce,
            'gas': 200000, 'gasPrice': gas
        })
        print("🔒 Commit...")
        if not sign_and_send(commit_tx, pk): return
    except Exception as e:
        print(f"❌ Commit error: {e}")
        return

    print("⏳ Tunggu 60 detik...")
    time.sleep(60)

    try:
        nonce = w3.eth.get_transaction_count(addr)
        duration = 31536000  # 1 tahun
        fee = Web3.to_wei(0.001, 'ether')
        register_tx = contract.functions.register(domain, addr, secret, duration).build_transaction({
            'from': addr, 'nonce': nonce,
            'gas': 300000, 'gasPrice': gas, 'value': fee
        })
        print("🔥 Register...")
        if sign_and_send(register_tx, pk):
            print(f"🎉 Berhasil mint: {domain}.phrs")
    except Exception as e:
        print(f"❌ Register error: {e}")

# === Main Loop ===
if __name__ == "__main__":
    while True:
        for w in wallets:
            domain = random_domain()
            register_domain(domain, w)
            print("🕐 Delay 5 detik ke domain berikutnya...")
            time.sleep(5)
