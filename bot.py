import os
import time
import secrets
import sys
from web3 import Web3
from dotenv import load_dotenv

# === Load ENV ===
load_dotenv()

RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = Web3.to_checksum_address("0x51be1ef20a1fd5179419738fc71d95a8b6f8a175")
ACCOUNTS_FILE = "accounts.txt"

# === Setup Web3 ===
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print(f"❌ Gagal konek ke RPC: {RPC_URL}")
    sys.exit(1)
else:
    print(f"✅ Terkoneksi ke Pharos RPC")

# === ABI Terdekompilasi dari bytecode ===
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
            lines = [line.strip() for line in f if line.strip()]
        wallets = []
        for key in lines:
            if not key.startswith("0x"):
                key = "0x" + key
            acct = w3.eth.account.from_key(key)
            wallets.append({"private_key": key, "address": acct.address})
        return wallets
    except Exception as e:
        print(f"❌ Gagal load akun dari {file}: {e}")
        return []

wallets = load_wallets(ACCOUNTS_FILE)
if not wallets:
    print("Tidak ada wallet ditemukan.")
    sys.exit(1)

print(f"🔑 Loaded {len(wallets)} wallet")

# === Gas Price Helper ===
def get_gas_price():
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(1, 'gwei')

# === Tx Sign & Send ===
def sign_and_send(txn, private_key):
    try:
        signed = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        status = "✅" if receipt.status == 1 else "❌"
        print(f"{status} Tx hash: {tx_hash.hex()}")
        return receipt.status == 1
    except Exception as e:
        print(f"❌ Gagal kirim tx: {e}")
        return False

# === Proses Mint Domain ===
def register_domain(domain, wallet):
    address = wallet["address"]
    pk = wallet["private_key"]
    print(f"\n🚀 Proses {domain}.phrs untuk {address}")

    try:
        secret = secrets.token_bytes(32)
        nonce = w3.eth.get_transaction_count(address)
        gas = get_gas_price()

        # Commit
        commitment = contract.functions.makeCommitment(domain, address, secret).call()
        tx_commit = contract.functions.commit(commitment).build_transaction({
            'from': address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': gas
        })
        print("🔒 Commit...")
        if not sign_and_send(tx_commit, pk): return

        print("⏳ Menunggu 60 detik sebelum register...")
        time.sleep(60)

        # Register
        nonce = w3.eth.get_transaction_count(address)
        duration = 31536000  # 1 tahun
        fee = Web3.to_wei(0.001, 'ether')
        tx_register = contract.functions.register(domain, address, secret, duration).build_transaction({
            'from': address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': gas,
            'value': fee
        })
        print("🔥 Register...")
        if sign_and_send(tx_register, pk):
            print(f"🎉 {domain}.phrs berhasil diregister!")
    except Exception as e:
        print(f"❌ Error saat proses: {e}")

# === MAIN ===
if __name__ == '__main__':
    domains = [
        "pharos1", "pharos2", "pharos3", "pharos4",
        "botalpha", "phrsbot1", "phrsbot2"
    ]

    print(f"\n📦 Total domain: {len(domains)} | 🧾 Wallets: {len(wallets)}\n")
    i = 0
    while i < len(domains):
        for wallet in wallets:
            if i >= len(domains):
                break
            register_domain(domains[i], wallet)
            i += 1
            if i < len(domains):
                print("🕐 Delay 5 detik ke domain berikutnya...")
                time.sleep(5)

    print("\n✅ Semua domain selesai diproses.")
