import os
import time
import secrets
import string
import random
import sys
from web3 import Web3
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv

load_dotenv()

# ===== KONFIGURASI =====
RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = "0x51Be1Ef20A1fD5179419738fC71D95a8B6F8A175"
CHAIN_ID = 688688  # Pharos Testnet Chain ID
ACCOUNTS_FILE = "accounts.txt"
MIN_DOMAIN_LENGTH = 3
MAX_DOMAIN_LENGTH = 10
MIN_COMMIT_WAIT = 60  # detik
GAS_LIMIT_COMMIT = 300000
GAS_LIMIT_REGISTER = 500000
REGISTRATION_FEE = Web3.to_wei(0.01, 'ether')
MAX_RETRIES = 3

# ===== ABI KONTRAK =====
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
    },
    {
        "inputs": [{"internalType": "string", "name": "name", "type": "string"}],
        "name": "available",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ===== INISIALISASI =====
w3 = Web3(Web3.HTTPProvider(RPC_URL))
print(f"⏳ Menghubungkan ke Pharos Testnet (Chain ID: {CHAIN_ID})...")

try:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI
    )
except Exception as e:
    print(f"❌ Gagal memuat kontrak: {e}")
    sys.exit(1)

if not w3.is_connected():
    print("❌ Gagal terhubung ke RPC")
    sys.exit(1)
else:
    print(f"✅ Terhubung ke Pharos Testnet | Chain ID: {w3.eth.chain_id}")

# ... (fungsi-fungsi lainnya tetap sama seperti sebelumnya)

def load_wallets():
    """Memuat wallet dari file teks"""
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        return [{
            'private_key': '0x' + l if not l.startswith('0x') else l,
            'address': w3.eth.account.from_key(l).address
        } for l in lines]
    except Exception as e:
        print(f"❌ Gagal memuat akun: {e}")
        return []

# ... (fungsi-fungsi lainnya seperti generate_valid_domain, get_gas_price, dll)

if __name__ == '__main__':
    wallets = load_wallets()
    print(f"\n🔑 Memuat {len(wallets)} wallet")
    
    for wallet in wallets:
        balance = w3.eth.get_balance(wallet['address'])
        min_required = REGISTRATION_FEE + Web3.to_wei(0.01, 'ether')
        
        if balance < min_required:
            print(f"\n⚠️ Saldo tidak cukup untuk {wallet['address']}")
            print(f"   Dibutuhkan: {Web3.from_wei(min_required, 'ether')} PHRS")
            print(f"   Saldo saat ini: {Web3.from_wei(balance, 'ether')} PHRS")
            continue
            
        print(f"\n💼 Memproses wallet: {wallet['address']}")
        mint_domain(wallet)
