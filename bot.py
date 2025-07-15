import os
import time
import secrets
import sys
from web3 import Web3
from dotenv import load_dotenv

# === Setup ===
load_dotenv()

RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = "0x51be1ef20a1fd5179419738fc71d95a8b6f8a175"
ACCOUNTS_FILE = "accounts.txt"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print(f"❌ Gagal konek ke RPC: {RPC_URL}")
    sys.exit(1)
else:
    print(f"✅ Terkoneksi ke Pharos RPC")

# === ABI (Contoh ABI, pastikan cocok dengan kontrak Pharos NS) ===
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

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

# === Load wallets ===
def load_keys(file):
    try:
        with open(file, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        keys = ['0x' + l if not l.startswith('0x') else l for l in lines]
        return [{'private_key': k, 'address': w3.eth.account.from_key(k).address} for k in keys]
    except Exception as e:
        print(f"❌ Gagal baca {file}: {e}")
        return []

wallets = load_keys(ACCOUNTS_FILE)
if not wallets:
    print("Tidak ada wallet ditemukan.")
    sys.exit(1)

print(f"🔑 Loaded {len(wallets)} wallet")

# === Helper ===
def get_gas_price():
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(1, 'gwei')

def sign_and_send(txn, pk):
    try:
        signed = w3.eth.account.sign_transaction(txn, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        status = "✅" if receipt.status == 1 else "❌"
        print(f"{status} Tx hash: {tx_hash.hex()}")
        return receipt.status == 1
    except Exception as e:
        print(f"❌ Tx error: {e}")
        return False

# === Proses domain ===
def register_domain(domain, wallet):
    addr = wallet['address']
    pk = wallet['private_key']
    print(f"\n🚀 Proses {domain}.phrs untuk {addr}")

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

    print("⏳ Tunggu 60 detik sebelum register...")
    time.sleep(60)

    try:
        nonce = w3.eth.get_transaction_count(addr)
        duration = 31536000
        fee = Web3.to_wei(0.001, 'ether')
        register_tx = contract.functions.register(domain, addr, secret, duration).build_transaction({
            'from': addr, 'nonce': nonce,
            'gas': 300000, 'gasPrice': gas, 'value': fee
        })
        print("🔥 Register...")
        if sign_and_send(register_tx, pk):
            print(f"🎉 Domain {domain}.phrs berhasil!")
    except Exception as e:
        print(f"❌ Register error: {e}")

# === Main ===
if __name__ == '__main__':
    domains = [
        "pharos1", "pharos2", "pharos3", "pharos4",
        "botalpha", "phrsbot1", "phrsbot2"
    ]

    print(f"Total domain: {len(domains)} | Wallets: {len(wallets)}")
    i = 0
    while i < len(domains):
        for w in wallets:
            if i >= len(domains): break
            register_domain(domains[i], w)
            i += 1
            if i < len(domains):
                print("🕐 Delay 5s ke domain berikutnya...")
                time.sleep(5)

    print("\n✅ Semua domain selesai.")
