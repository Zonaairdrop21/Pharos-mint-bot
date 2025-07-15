import os
import time
import secrets
import random
import string
import sys
from web3 import Web3
from dotenv import load_dotenv
from eth_account import Account

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

# === ABI (hanya method yang dibutuhkan) ===
CONTRACT_ABI = [
    {
        "name": "commit",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "commitment", "type": "bytes32"}],
        "outputs": []
    },
    {
        "name": "register",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "owner", "type": "address"},
            {"name": "secret", "type": "bytes32"},
            {"name": "duration", "type": "uint256"}
        ],
        "outputs": []
    },
    {
        "name": "makeCommitment",
        "type": "function",
        "stateMutability": "pure",
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "owner", "type": "address"},
            {"name": "secret", "type": "bytes32"}
        ],
        "outputs": [{"name": "", "type": "bytes32"}]
    }
]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# === Load Wallets ===
def load_wallets(file):
    try:
        with open(file, 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
            return [{'private_key': k, 'address': Account.from_key(k).address} for k in keys]
    except Exception as e:
        print(f"❌ Gagal baca file: {e}")
        return []

wallets = load_wallets(ACCOUNTS_FILE)
if not wallets:
    print("Tidak ada wallet ditemukan!")
    sys.exit(1)
print(f"🔑 Loaded {len(wallets)} wallet")

# === Helper ===
def get_gas():
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(1, 'gwei')

def random_domain(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def sign_and_send(txn, pk):
    try:
        signed = w3.eth.account.sign_transaction(txn, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f"  ✅ Tx hash: {tx_hash.hex()}")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        return True
    except Exception as e:
        print(f"  ❌ Tx error: {e}")
        return False

# === Main ===
while True:
    for wallet in wallets:
        addr = wallet['address']
        pk = wallet['private_key']
        domain = random_domain()
        print(f"\n🚀 Coba mint domain: {domain}.phrs untuk {addr}")

        secret = secrets.token_bytes(32)
        gas = get_gas()
        nonce = w3.eth.get_transaction_count(addr)

        try:
            commitment = contract.functions.makeCommitment(domain, addr, secret).call()
            txn = contract.functions.commit(commitment).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': gas
            })
            print("🔒 Step 1: Commit name", domain + ".phrs")
            if not sign_and_send(txn, pk):
                continue
        except Exception as e:
            print(f"❌ Commit error: {e}")
            print("🕐 Delay 5 detik ke domain berikutnya...")
            time.sleep(5)
            continue

        print("⏳ Waiting 60 seconds before registering...")
        for i in range(60):
            print(f"Waiting: {int((i+1)/60*100)}%", end='\r')
            time.sleep(1)

        try:
            nonce = w3.eth.get_transaction_count(addr)
            txn2 = contract.functions.register(domain, addr, secret, 31536000).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': gas,
                'value': Web3.to_wei(0.001, 'ether')
            })
            print("🔥 Step 2: Register name", domain + ".phrs")
            if sign_and_send(txn2, pk):
                print(f"🎉 Minted domain: {domain}.phrs")
        except Exception as e:
            print(f"❌ Register error: {e}")

        print("🕐 Delay 5 detik sebelum domain berikutnya...")
        time.sleep(5)
