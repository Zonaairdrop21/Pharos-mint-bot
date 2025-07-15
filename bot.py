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

# ===== FUNGSI UTAMA =====
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

def generate_valid_domain():
    """Generate nama domain yang valid"""
    length = random.randint(MIN_DOMAIN_LENGTH, MAX_DOMAIN_LENGTH)
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def get_gas_price():
    """Mendapatkan gas price"""
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(2, 'gwei')  # Default untuk testnet

def send_transaction(tx, private_key, action_name=""):
    """Mengirim transaksi"""
    try:
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"⏳ {action_name} TX dikirim: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status == 1:
            print(f"✅ {action_name} berhasil")
            return True
        else:
            print(f"❌ {action_name} gagal")
            return False
    except ContractLogicError as e:
        print(f"❌ Error kontrak: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

def mint_domain(wallet):
    """Proses utama untuk mint domain"""
    address = wallet['address']
    private_key = wallet['private_key']
    
    for attempt in range(MAX_RETRIES):
        domain = generate_valid_domain()
        print(f"\n🔷 Percobaan #{attempt + 1} | Domain: {domain}.phrs")
        
        try:
            # 1. Buat komitmen
            secret = secrets.token_bytes(32)
            commitment = contract.functions.makeCommitment(
                domain,
                address,
                secret
            ).call()
            
            # 2. Commit
            commit_tx = contract.functions.commit(commitment).build_transaction({
                'from': address,
                'nonce': w3.eth.get_transaction_count(address),
                'gas': GAS_LIMIT_COMMIT,
                'gasPrice': get_gas_price(),
                'chainId': CHAIN_ID
            })
            
            if not send_transaction(commit_tx, private_key, "Commit"):
                continue
                
            # 3. Tunggu
            print(f"⏳ Menunggu {MIN_COMMIT_WAIT} detik...")
            time.sleep(MIN_COMMIT_WAIT)
            
            # 4. Register
            register_tx = contract.functions.register(
                domain,
                address,
                secret,
                31536000  # 1 tahun
            ).build_transaction({
                'from': address,
                'nonce': w3.eth.get_transaction_count(address),
                'gas': GAS_LIMIT_REGISTER,
                'gasPrice': get_gas_price(),
                'value': REGISTRATION_FEE,
                'chainId': CHAIN_ID
            })
            
            if send_transaction(register_tx, private_key, "Register"):
                print(f"🎉 Berhasil mendaftarkan domain: {domain}.phrs")
                return True
                
        except Exception as e:
            print(f"⚠️ Error: {e}")
        
        time.sleep(5)
    
    print("❌ Gagal setelah maksimal percobaan")
    return False

# ===== EKSEKUSI UTAMA =====
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
