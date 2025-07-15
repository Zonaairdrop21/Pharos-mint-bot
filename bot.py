import os
import time
import secrets
import string
import random
import sys
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi
RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = "0x51Be1Ef20A1fD5179419738fC71D95a8B6F8A175"
ACCOUNTS_FILE = "accounts.txt"
MIN_COMMIT_WAIT = 120  # Waktu tunggu antara commit dan register (detik)
GAS_LIMIT_COMMIT = 300000
GAS_LIMIT_REGISTER = 500000
REGISTRATION_FEE = Web3.to_wei(0.01, 'ether')  # Biaya registrasi

# Inisialisasi Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=[
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
)

if not w3.is_connected():
    print("❌ Gagal konek ke RPC")
    sys.exit(1)
else:
    print("✅ Terkoneksi ke Pharos RPC")

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

def random_domain(length=8):
    """Generate nama domain acak"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def get_gas_price():
    """Mendapatkan gas price dengan fallback default"""
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(10, 'gwei')  # Default 10 gwei

def sign_and_send(tx, pk):
    """Menandatangani dan mengirim transaksi"""
    try:
        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        
        if receipt.status == 1:
            print(f"✅ TX berhasil: {tx_hash.hex()}")
            return True
        else:
            print(f"❌ TX gagal: {tx_hash.hex()}")
            return False
    except Exception as e:
        print(f"❌ Error TX: {str(e)}")
        return False

def check_domain_available(domain):
    """Memeriksa ketersediaan domain"""
    try:
        return contract.functions.available(domain).call()
    except Exception as e:
        print(f"❌ Gagal memeriksa ketersediaan domain: {e}")
        return False

def mint_domain(wallet):
    """Proses minting domain"""
    addr = wallet['address']
    pk = wallet['private_key']

    while True:
        domain = random_domain()
        full_domain = f"{domain}.phrs"
        print(f"\n🚀 Mencoba mint domain: {full_domain} untuk {addr}")

        # 1. Periksa ketersediaan domain
        if not check_domain_available(domain):
            print(f"❌ Domain {full_domain} tidak tersedia")
            time.sleep(5)
            continue

        # 2. Persiapkan data untuk commit
        secret = secrets.token_bytes(32)
        wallet['current_secret'] = secret
        gas_price = get_gas_price()
        nonce = w3.eth.get_transaction_count(addr)

        try:
            # 3. Buat dan kirim commit
            commitment = contract.functions.makeCommitment(
                domain, 
                addr, 
                secret
            ).call()

            commit_tx = contract.functions.commit(commitment).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': GAS_LIMIT_COMMIT,
                'gasPrice': gas_price
            })

            if not sign_and_send(commit_tx, pk):
                print("❌ Gagal commit, mencoba domain lain...")
                time.sleep(5)
                continue

            # 4. Tunggu sebelum register
            print(f"⏳ Menunggu {MIN_COMMIT_WAIT} detik sebelum register...")
            time.sleep(MIN_COMMIT_WAIT)

            # 5. Proses register
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
                'value': REGISTRATION_FEE
            })

            if sign_and_send(register_tx, pk):
                print(f"🎉 Berhasil mendaftarkan domain: {full_domain}")
                break
            else:
                print("❌ Gagal register, mencoba domain lain...")

        except Exception as e:
            print(f"❌ Error saat proses: {str(e)}")

        print("🕐 Menunggu 5 detik sebelum mencoba domain berikutnya...")
        time.sleep(5)

if __name__ == '__main__':
    wallets = load_wallets()
    print(f"🔑 Memuat {len(wallets)} wallet")
    
    for wallet in wallets:
        # Periksa saldo sebelum memulai
        balance = w3.eth.get_balance(wallet['address'])
        print(f"\nAlamat: {wallet['address']}")
        print(f"Saldo: {Web3.from_wei(balance, 'ether')} ETH")
        
        if balance < (REGISTRATION_FEE + Web3.to_wei(0.01, 'ether')):  # Fee + buffer gas
            print("❌ Saldo tidak cukup, lewati wallet ini")
            continue
            
        mint_domain(wallet)
