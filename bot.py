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

# ===== KONFIGURASI PHAROS TESTNET =====
RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = "0x51Be1Ef20A1fD5179419738fC71D95a8B6F8A175"
CHAIN_ID = 688688  # Chain ID Pharos Testnet
SYMBOL = "PHRS"    # Simbol network
ACCOUNTS_FILE = "accounts.txt"
MIN_DOMAIN_LENGTH = 3
MAX_DOMAIN_LENGTH = 10
MIN_COMMIT_WAIT = 60  # 1 menit
GAS_LIMIT_COMMIT = 300000
GAS_LIMIT_REGISTER = 500000
REGISTRATION_FEE = Web3.to_wei(0.01, 'ether')  # 0.01 PHRS
MAX_RETRIES = 3

# ===== INISIALISASI WEB3 =====
w3 = Web3(Web3.HTTPProvider(RPC_URL))
print(f"⏳ Menghubungkan ke Pharos Testnet (Chain ID: {CHAIN_ID})...")

contract_abi = [...]  # Gunakan ABI yang sama seperti sebelumnya

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=contract_abi
)

if not w3.is_connected():
    print(f"❌ Gagal terhubung ke Pharos Testnet")
    sys.exit(1)
else:
    print(f"✅ Terhubung ke Pharos Testnet | Chain ID: {w3.eth.chain_id}")

def get_gas_price():
    """Gas price khusus untuk testnet"""
    try:
        # Untuk testnet, gunakan gas price lebih rendah
        return Web3.to_wei(2, 'gwei')  # 2 Gwei untuk testnet
    except:
        return Web3.to_wei(2, 'gwei')

def send_transaction(tx, pk, action_name=""):
    """Menambahkan penanganan khusus untuk testnet"""
    try:
        # Pastikan chain ID sesuai
        tx['chainId'] = CHAIN_ID
        
        signed_tx = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"⏳ {action_name} TX dikirim: {tx_hash.hex()}")
        print(f"🔗 Explorer: https://pharos-testnet.socialscan.io/tx/{tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        if receipt.status == 1:
            print(f"✅ {action_name} berhasil (Gas used: {receipt.gasUsed})")
            return True
        else:
            print(f"❌ {action_name} gagal (Block: {receipt.blockNumber})")
            return False
    except ContractLogicError as e:
        print(f"❌ Error kontrak: {e.message}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    return False

def mint_domain(wallet):
    """Proses minting dengan penyesuaian testnet"""
    addr = wallet['address']
    pk = wallet['private_key']
    
    print(f"\n🔷 Memproses wallet: {addr[:6]}...{addr[-4:]}")
    print(f"💳 Saldo: {Web3.from_wei(w3.eth.get_balance(addr), 'ether')} {SYMBOL}")

    attempt = 0
    while attempt < MAX_RETRIES:
        domain = ''.join(random.choices(string.ascii_lowercase, k=random.randint(MIN_DOMAIN_LENGTH, MAX_DOMAIN_LENGTH)))
        full_domain = f"{domain}.{SYMBOL.lower()}"
        
        print(f"\n🔷 Percobaan #{attempt+1}/{MAX_RETRIES}")
        print(f"🌐 Domain: {full_domain}")

        try:
            # 1. Buat komitmen
            secret = secrets.token_bytes(32)
            commitment = contract.functions.makeCommitment(
                domain,
                addr,
                secret
            ).call()

            # 2. Commit
            commit_tx = contract.functions.commit(commitment).build_transaction({
                'from': addr,
                'nonce': w3.eth.get_transaction_count(addr),
                'gas': GAS_LIMIT_COMMIT,
                'gasPrice': get_gas_price(),
                'chainId': CHAIN_ID
            })

            if not send_transaction(commit_tx, pk, "Commit"):
                continue

            # 3. Tunggu
            print(f"⏳ Menunggu {MIN_COMMIT_WAIT} detik...")
            time.sleep(MIN_COMMIT_WAIT)

            # 4. Register
            register_tx = contract.functions.register(
                domain,
                addr,
                secret,
                31536000  # 1 tahun
            ).build_transaction({
                'from': addr,
                'nonce': w3.eth.get_transaction_count(addr),
                'gas': GAS_LIMIT_REGISTER,
                'gasPrice': get_gas_price(),
                'value': REGISTRATION_FEE,
                'chainId': CHAIN_ID
            })

            if send_transaction(register_tx, pk, "Register"):
                print(f"🎉 Sukses! Domain: {full_domain}")
                return True

        except Exception as e:
            print(f"⚠️ Error: {str(e)}")
            if "execution reverted" in str(e):
                print("ℹ️ Kemungkinan domain tidak valid atau sudah terdaftar")

        attempt += 1
        time.sleep(5)
    
    print("❌ Gagal setelah maksimal percobaan")
    return False

if __name__ == '__main__':
    wallets = load_wallets()
    print(f"\n🔑 Total wallet: {len(wallets)}")
    
    for wallet in wallets:
        balance = w3.eth.get_balance(wallet['address'])
        if balance < Web3.to_wei(0.02, 'ether'):  # Minimal 0.02 PHRS
            print(f"⚠️ Saldo tidak cukup untuk {wallet['address'][:6]}...{wallet['address'][-4:]}")
            continue
            
        mint_domain(wallet)
        print("\n" + "="*50 + "\n")
