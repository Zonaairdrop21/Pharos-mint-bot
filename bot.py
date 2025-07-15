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
ACCOUNTS_FILE = "accounts.txt"
MIN_DOMAIN_LENGTH = 3  # Panjang minimal domain
MAX_DOMAIN_LENGTH = 10  # Panjang maksimal domain
MIN_COMMIT_WAIT = 60  # Waktu tunggu minimal commit (detik)
GAS_LIMIT_COMMIT = 300000
GAS_LIMIT_REGISTER = 500000
REGISTRATION_FEE = Web3.to_wei(0.01, 'ether')  # Biaya registrasi
MAX_RETRIES = 3  # Jumlah percobaan per domain

# ===== INISIALISASI WEB3 =====
w3 = Web3(Web3.HTTPProvider(RPC_URL))
print(f"⏳ Menghubungkan ke RPC... ({RPC_URL})")

contract_abi = [
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

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

if not w3.is_connected():
    print("❌ Gagal terhubung ke RPC")
    sys.exit(1)
else:
    print("✅ Terhubung ke Pharos RPC")

# ===== FUNGSI UTILITAS =====
def load_wallets():
    """Memuat wallet dari file teks"""
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        
        wallets = []
        for l in lines:
            try:
                pk = '0x' + l if not l.startswith('0x') else l
                wallets.append({
                    'private_key': pk,
                    'address': w3.eth.account.from_key(pk).address
                })
            except Exception as e:
                print(f"⚠️ Gagal memproses private key: {e}")
        
        return wallets
    except Exception as e:
        print(f"❌ Gagal memuat akun: {e}")
        return []

def generate_valid_domain():
    """Generate nama domain yang valid"""
    length = random.randint(MIN_DOMAIN_LENGTH, MAX_DOMAIN_LENGTH)
    while True:
        domain = ''.join(random.choices(string.ascii_lowercase, k=length))
        # Tambahkan validasi tambahan jika diperlukan
        if len(domain) >= MIN_DOMAIN_LENGTH:
            return domain

def get_gas_price():
    """Mendapatkan gas price dengan fallback default"""
    try:
        return w3.eth.gas_price
    except Exception as e:
        print(f"⚠️ Gagal mendapatkan gas price: {e}, menggunakan default")
        return Web3.to_wei(10, 'gwei')

def send_transaction(tx, pk, action_name=""):
    """Menandatangani dan mengirim transaksi"""
    try:
        signed_tx = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"⏳ {action_name} TX dikirim: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if receipt.status == 1:
            print(f"✅ {action_name} berhasil")
            return True
        else:
            print(f"❌ {action_name} gagal (status: {receipt.status})")
            return False
    except ContractLogicError as e:
        print(f"❌ Error kontrak saat {action_name}: {e}")
    except Exception as e:
        print(f"❌ Error saat {action_name}: {str(e)}")
    return False

def check_domain_available(domain):
    """Memeriksa ketersediaan domain"""
    try:
        return contract.functions.available(domain).call()
    except Exception as e:
        print(f"⚠️ Gagal memeriksa domain {domain}: {e}")
        return False

# ===== PROSES MINTING =====
def mint_domain(wallet):
    """Proses minting domain"""
    addr = wallet['address']
    pk = wallet['private_key']
    
    print(f"\n🔷 Memproses wallet: {addr}")
    print(f"💳 Saldo: {Web3.from_wei(w3.eth.get_balance(addr), 'ether')} ETH")

    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        domain = generate_valid_domain()
        full_domain = f"{domain}.phrs"
        
        print(f"\n🔷 Percobaan #{attempt} | Domain: {full_domain}")

        # 1. Periksa ketersediaan domain
        if not check_domain_available(domain):
            print(f"⚠️ Domain {full_domain} tidak tersedia")
            time.sleep(2)
            continue

        # 2. Persiapkan data untuk commit
        secret = secrets.token_bytes(32)
        gas_price = get_gas_price()
        nonce = w3.eth.get_transaction_count(addr)

        try:
            # 3. Buat commitment
            print("⏳ Membuat commitment...")
            commitment = contract.functions.makeCommitment(
                domain, 
                addr, 
                secret
            ).call()

            # 4. Kirim commit transaction
            print("⏳ Mengirim commit...")
            commit_tx = contract.functions.commit(commitment).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': GAS_LIMIT_COMMIT,
                'gasPrice': gas_price,
                'chainId': w3.eth.chain_id
            })

            if not send_transaction(commit_tx, pk, "Commit"):
                print("⚠️ Gagal commit, mencoba domain lain...")
                time.sleep(5)
                continue

            # 5. Tunggu sebelum register
            print(f"⏳ Menunggu {MIN_COMMIT_WAIT} detik sebelum register...")
            time.sleep(MIN_COMMIT_WAIT)

            # 6. Proses register
            print("⏳ Memproses register...")
            nonce = w3.eth.get_transaction_count(addr)
            register_tx = contract.functions.register(
                domain,
                addr,
                secret,
                31536000  # 1 tahun dalam detik
            ).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': GAS_LIMIT_REGISTER,
                'gasPrice': gas_price,
                'value': REGISTRATION_FEE,
                'chainId': w3.eth.chain_id
            })

            if send_transaction(register_tx, pk, "Register"):
                print(f"🎉 Berhasil mendaftarkan domain: {full_domain}")
                return True
            else:
                print("⚠️ Gagal register, mencoba domain lain...")

        except Exception as e:
            print(f"❌ Error fatal: {str(e)}")
            if "execution reverted" in str(e):
                print("ℹ️ Kemungkinan domain tidak memenuhi syarat kontrak")

        time.sleep(5)
    
    print(f"❌ Gagal setelah {MAX_RETRIES} percobaan")
    return False

# ===== MAIN EXECUTION =====
if __name__ == '__main__':
    wallets = load_wallets()
    if not wallets:
        print("❌ Tidak ada wallet yang valid")
        sys.exit(1)
    
    print(f"\n🔑 Memuat {len(wallets)} wallet")
    
    for wallet in wallets:
        # Periksa saldo
        balance = w3.eth.get_balance(wallet['address'])
        min_required = REGISTRATION_FEE + Web3.to_wei(0.01, 'ether')
        
        if balance < min_required:
            print(f"\n⚠️ Saldo tidak cukup untuk {wallet['address']}")
            print(f"   Dibutuhkan: {Web3.from_wei(min_required, 'ether')} ETH")
            print(f"   Saldo saat ini: {Web3.from_wei(balance, 'ether')} ETH")
            continue
            
        print(f"\n💼 Memproses wallet: {wallet['address']}")
        mint_domain(wallet)
