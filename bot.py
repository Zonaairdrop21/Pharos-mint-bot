import threading
import queue
import random
import time
import os
import string
from web3 import Web3, HTTPProvider
from eth_account import Account
from hexbytes import HexBytes
import logging
from typing import List, Tuple
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib3.exceptions import HTTPError

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Konfigurasi dasar (beberapa akan diatur oleh input pengguna)
CONFIG = {
    'RPC_URL': "https://testnet.dplabs-internal.com",
    'CONTROLLER_ADDRESS': "0x51be1ef20a1fd5179419738fc71d95a8b6f8a175",
    'DURATION': 31536000, # Durasi pendaftaran dalam detik (1 tahun)
    'RESOLVER': "0x9a43dcA1C3BB268546b98eb2AB1401bFc5b58505",
    'DATA': [],
    'REVERSE_RECORD': True,
    'OWNER_CONTROLLED_FUSES': 0,
    'CHAIN_ID': 688688  # ID rantai untuk transaksi
}

# ABI minimal untuk kontrak controller (sesuai yang Anda berikan)
CONTROLLER_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "owner", "type": "address"},
            {"name": "duration", "type": "uint256"},
            {"name": "secret", "type": "bytes32"},
            {"name": "resolver", "type": "address"},
            {"name": "data", "type": "bytes[]"},
            {"name": "reverseRecord", "type": "bool"},
            {"name": "ownerControlledFuses", "type": "uint16"}
        ],
        "name": "makeCommitment",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "commitment", "type": "bytes32"}],
        "name": "commit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "duration", "type": "uint256"}
        ],
        "name": "rentPrice",
        "outputs": [
            {
                "components": [
                    {"name": "base", "type": "uint256"},
                    {"name": "premium", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "owner", "type": "address"},
            {"name": "duration", "type": "uint256"},
            {"name": "secret", "type": "bytes32"},
            {"name": "resolver", "type": "address"},
            {"name": "data", "type": "bytes[]"},
            {"name": "reverseRecord", "type": "bool"},
            {"name": "ownerControlledFuses", "type": "uint16"}
        ],
        "name": "register",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

def clear_screen():
    """Membersihkan layar konsol."""
    os.system('cls' if os.name == 'nt' else 'clear')

def load_file_lines(filename: str) -> List[str]:
    """Memuat baris dari file teks."""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"File '{filename}' tidak ditemukan.")
        return []

def random_name(length: int = 9) -> str:
    """
    Menghasilkan nama domain acak yang terdiri dari huruf kecil (a-z), angka (0-9),
    dan tanda hubung (-).
    Aturan:
    - Dimulai dan diakhiri dengan huruf atau angka.
    - Tidak ada tanda hubung ganda (misalnya "a--b").
    - Panjang nama domain akan sesuai dengan parameter 'length'.
    """
    if length < 3: 
        length = 3 

    chars_letters = string.ascii_lowercase
    chars_letters_digits = string.ascii_lowercase + string.digits
    
    name_list = []

    # Karakter pertama harus huruf
    name_list.append(random.choice(chars_letters))

    for _ in range(length - 1):
        if name_list[-1] == '-':
            name_list.append(random.choice(chars_letters_digits))
        else:
            name_list.append(random.choice(chars_letters_digits + '-' * 1)) 

    if name_list[-1] == '-':
        name_list[-1] = random.choice(chars_letters_digits)

    cleaned_name = []
    for i, char in enumerate(name_list):
        if char == '-' and i > 0 and cleaned_name and cleaned_name[-1] == '-':
            cleaned_name.append(random.choice(chars_letters_digits))
        else:
            cleaned_name.append(char)
            
    while len(cleaned_name) < length:
        if cleaned_name and cleaned_name[-1] == '-':
            cleaned_name.append(random.choice(chars_letters_digits))
        else:
            cleaned_name.append(random.choice(chars_letters_digits + '-'))

    final_result = ''.join(cleaned_name[:length])
    if final_result.startswith('-'):
        final_result = random.choice(chars_letters_digits) + final_result[1:]
    if final_result.endswith('-'):
        final_result = final_result[:-1] + random.choice(chars_letters_digits)
    
    final_result = final_result.replace('--', random.choice(chars_letters_digits) + random.choice(chars_letters_digits))
    
    while len(final_result) < length:
        final_result += random.choice(chars_letters_digits)

    return final_result[:length]


def test_proxy(proxy: str) -> Tuple[str, bool]:
    """Menguji apakah proxy berfungsi dengan mencoba koneksi ke api.ipify.org."""
    try:
        response = requests.get('https://api.ipify.org', proxies={'http': proxy, 'https': proxy}, timeout=5)
        return proxy, response.status_code == 200
    except (requests.RequestException, HTTPError) as e:
        logger.debug(f"Proxy {proxy} gagal diuji: {e}")
        return proxy, False

def create_web3_instance(proxy: str = None) -> Web3:
    """Membuat instance Web3, dengan atau tanpa proxy."""
    if proxy:
        session = requests.Session()
        session.proxies = {'http': proxy, 'https': proxy}
        return Web3(HTTPProvider(CONFIG['RPC_URL'], session=session))
    return Web3(HTTPProvider(CONFIG['RPC_URL']))

def validate_private_key(private_key: str) -> bool:
    """Memvalidasi format kunci pribadi."""
    if private_key.startswith('0x'):
        private_key = private_key[2:]
    if len(private_key) != 64 or not all(c in string.hexdigits for c in private_key):
        return False
    return True

# Counter untuk sukses dan gagal
success_count = 0
failed_count = 0
total_tasks = 0
current_tasks_processed = 0
processed_lock = threading.Lock() 

def register_domain_single_task(private_key: str, index: int, reg_index: int, proxy: str = None) -> None:
    """
    Melakukan satu siklus penuh pendaftaran domain (Commit -> Jeda -> Register).
    Ini dirancang untuk dijalankan secara sekuensial PER TUGAS di dalam thread-nya.
    """
    global success_count, failed_count, current_tasks_processed

    MAX_RETRY = 5
    retry = 0
    
    if not validate_private_key(private_key):
        logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Kunci pribadi tidak valid, melewati pendaftaran.")
        with processed_lock:
            failed_count += 1
            current_tasks_processed += 1
        return

    w3 = create_web3_instance(proxy)
    
    try:
        controller_address = w3.to_checksum_address(CONFIG['CONTROLLER_ADDRESS'])
        resolver_address = w3.to_checksum_address(CONFIG['RESOLVER'])
    except ValueError as e:
        logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Alamat kontrak atau resolver tidak valid dalam konfigurasi: {e}")
        with processed_lock:
            failed_count += 1
            current_tasks_processed += 1
        return

    domain_registered = False
    name = random_name() # Nama domain dihasilkan di sini untuk setiap percobaan

    while retry < MAX_RETRY:
        try:
            account = Account.from_key(private_key)
            controller = w3.eth.contract(address=controller_address, abi=CONTROLLER_ABI)
            
            owner = account.address
            secret = HexBytes(os.urandom(32))
            
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Memulai pendaftaran {name}.phrs...")

            # 1. Buat commitment
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] COMMIT untuk {name}.phrs - Membuat commitment...")
            commitment = controller.functions.makeCommitment(
                name,
                owner,
                CONFIG['DURATION'],
                secret,
                resolver_address,
                CONFIG['DATA'],
                CONFIG['REVERSE_RECORD'],
                CONFIG['OWNER_CONTROLLED_FUSES']
            ).call()
            # logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Commitment {commitment.hex()} dibuat.")

            # 2. Kirim transaksi commit
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] COMMIT untuk {name}.phrs - Mengirim transaksi...")
            tx_commit = controller.functions.commit(commitment).build_transaction({
                'from': owner,
                'nonce': w3.eth.get_transaction_count(owner),
                'gas': 200000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })
            
            logger.debug(f"DEBUG: Tipe tx_commit sebelum sign: {type(tx_commit)}")
            signed_tx_commit = account.sign_transaction(tx_commit)
            logger.debug(f"DEBUG: Tipe signed_tx_commit setelah sign: {type(signed_tx_commit)}")
            logger.debug(f"DEBUG: Atribut signed_tx_commit: {dir(signed_tx_commit)}")
            
            try:
                # --- PERBAIKAN DI SINI: Ganti rawTransaction ke raw_transaction ---
                tx_hash_commit = w3.eth.send_raw_transaction(signed_tx_commit.raw_transaction)
            except AttributeError as e:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] KRITIS: Gagal akses raw_transaction: {e}")
                logger.error(f"DEBUG: signed_tx_commit type: {type(signed_tx_commit)}")
                logger.error(f"DEBUG: signed_tx_commit dir: {dir(signed_tx_commit)}")
                raise # Re-raise untuk memicu retry

            receipt_commit = w3.eth.wait_for_transaction_receipt(tx_hash_commit)
            
            if receipt_commit.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] COMMIT untuk {name}.phrs - Berhasil! TX Hash: {tx_hash_commit.hex()}")
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] COMMIT untuk {name}.phrs - Gagal. TX Hash: {tx_hash_commit.hex()}")
                raise Exception("Transaksi commitment gagal.")

            # 3. Tunggu minCommitmentAge (60 detik)
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] MENUNGGU 60 detik untuk {name}.phrs...")
            time.sleep(60)

            # 4. Hitung harga sewa domain
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] REGISTER untuk {name}.phrs - Menghitung harga sewa...")
            price = controller.functions.rentPrice(name, CONFIG['DURATION']).call()
            value = price[0] + price[1]
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] REGISTER untuk {name}.phrs - Harga sewa: {w3.from_wei(value, 'ether')} ETH.")

            # 5. Kirim transaksi pendaftaran
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] REGISTER untuk {name}.phrs - Mengirim transaksi...")
            tx_register = controller.functions.register(
                name,
                owner,
                CONFIG['DURATION'],
                secret,
                resolver_address,
                CONFIG['DATA'],
                CONFIG['REVERSE_RECORD'],
                CONFIG['OWNER_CONTROLLED_FUSES']
            ).build_transaction({
                'from': owner,
                'nonce': w3.eth.get_transaction_count(owner),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
                'value': value,
                'chainId': CONFIG['CHAIN_ID']
            })
            
            logger.debug(f"DEBUG: Tipe tx_register sebelum sign: {type(tx_register)}")
            signed_tx_register = account.sign_transaction(tx_register)
            logger.debug(f"DEBUG: Tipe signed_tx_register setelah sign: {type(signed_tx_register)}")
            logger.debug(f"DEBUG: Atribut signed_tx_register: {dir(signed_tx_register)}")

            try:
                # --- PERBAIKAN DI SINI: Ganti rawTransaction ke raw_transaction ---
                tx_hash_register = w3.eth.send_raw_transaction(signed_tx_register.raw_transaction)
            except AttributeError as e:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] KRITIS: Gagal akses raw_transaction: {e}")
                logger.error(f"DEBUG: signed_tx_register type: {type(signed_tx_register)}")
                logger.error(f"DEBUG: signed_tx_register dir: {dir(signed_tx_register)}")
                raise # Re-raise untuk memicu retry
            
            receipt_register = w3.eth.wait_for_transaction_receipt(tx_hash_register)
            
            if receipt_register.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] REGISTER untuk {name}.phrs - BERHASIL! TX Hash: {tx_hash_register.hex()}")
                domain_registered = True
                break
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] REGISTER untuk {name}.phrs - GAGAL. TX Hash: {tx_hash_register.hex()}")
                raise Exception("Transaksi pendaftaran gagal.")

        except Exception as err:
            retry += 1
            msg = str(err)[:150] + '...' if len(str(err)) > 150 else str(err)
            logger.warning(f"[Wallet #{index+1} | Percobaan {reg_index}] Error saat memproses {name}.phrs: {msg} - mencoba lagi ({retry}/{MAX_RETRY}) dalam 60 detik...")
            time.sleep(60)
                
    with processed_lock:
        if domain_registered:
            success_count += 1
        else:
            failed_count += 1
        current_tasks_processed += 1
    
    print_progress()

def print_progress():
    """Mencetak status progres ke konsol."""
    clear_screen()
    current_time_str = time.strftime("%H:%M:%S %d.%m.%y")
    
    print(f"""
[ WARDEN BOT ]
{current_time_str}

Automated Protocol Utility
by ZonaAirdrop (@ZonaAirdrop)

Total Tasks: {total_tasks}
Success: {success_count}
Failed: {failed_count}
Processed: {current_tasks_processed}/{total_tasks}
""")

def main():
    """Fungsi utama untuk menjalankan proses pendaftaran domain secara paralel."""
    global success_count, failed_count, total_tasks, current_tasks_processed

    clear_screen()
    print("====================================")
    print("     PHAROS MINT BOT")
    print("====================================")
    print("[1] Jalankan dengan Proxy Pribadi")
    print("[2] Jalankan tanpa Proxy")
    print("====================================")

    use_proxy_option = input("Pilih opsi (1 atau 2): ").strip()
    
    proxy_list = []
    if use_proxy_option == '1':
        raw_proxy_list = load_file_lines("proxy.txt")
        if not raw_proxy_list:
            logger.warning("Tidak ditemukan proxy di 'proxy.txt'. Akan berjalan tanpa proxy.")
            use_proxy_option = '2'
        else:
            logger.info(f"Menguji {len(raw_proxy_list)} proxy yang ditemukan...")
            proxy_test_workers = min(len(raw_proxy_list), os.cpu_count() * 2 if os.cpu_count() else 10)
            if proxy_test_workers == 0 and len(raw_proxy_list) > 0:
                 proxy_test_workers = 1 

            if proxy_test_workers > 0:
                with ThreadPoolExecutor(max_workers=proxy_test_workers) as executor:
                    tested_proxies_results = list(executor.map(test_proxy, raw_proxy_list))
                proxy_list = [p for p, success in tested_proxies_results if success]
            
            if not proxy_list:
                logger.warning("Tidak ada proxy yang berfungsi dari 'proxy.txt'. Bot akan berjalan tanpa proxy.")
                use_proxy_option = '2'
            else:
                logger.info(f"{len(proxy_list)} proxy berfungsi dan akan digunakan.")

    pk_list = load_file_lines("accounts.txt")
    
    if not pk_list:
        logger.error("Tidak ditemukan kunci pribadi di 'accounts.txt'. Pastikan file ada dan berisi kunci pribadi.")
        input("Tekan Enter untuk keluar...")
        return

    print(f"\nTotal Akun yang ditemukan: {len(pk_list)}")

    reg_per_key_str = input("Mau berapa domain yang ingin di-generate per akun? (misal: 1): ").strip()
    try:
        CONFIG['REG_PER_KEY'] = int(reg_per_key_str)
        if CONFIG['REG_PER_KEY'] <= 0:
            raise ValueError
    except ValueError:
        logger.error("Input tidak valid. Jumlah domain harus angka positif.")
        input("Tekan Enter untuk keluar...")
        return
    
    max_concurrency_str = input("Masukkan jumlah thread/konkurensi maksimal (misal: 10): ").strip()
    try:
        CONFIG['MAX_CONCURRENCY'] = int(max_concurrency_str)
        if CONFIG['MAX_CONCURRENCY'] <= 0:
            raise ValueError
    except ValueError:
        logger.error("Input tidak valid. Jumlah thread harus angka positif.")
        input("Tekan Enter untuk keluar...")
        return

    success_count = 0
    failed_count = 0
    current_tasks_processed = 0

    tasks_to_process = [(pk, idx, i + 1) for idx, pk in enumerate(pk_list) for i in range(CONFIG['REG_PER_KEY'])]
    random.shuffle(tasks_to_process)
    total_tasks = len(tasks_to_process)

    print_progress()

    logger.info(f"Memulai pendaftaran domain untuk {len(pk_list)} akun, total {total_tasks} pendaftaran.")
    
    with ThreadPoolExecutor(max_workers=CONFIG['MAX_CONCURRENCY']) as executor:
        futures = []
        for pk, idx, reg_idx in tasks_to_process:
            chosen_proxy = None
            if use_proxy_option == '1' and proxy_list:
                chosen_proxy = random.choice(proxy_list)
            
            futures.append(executor.submit(register_domain_single_task, pk, idx, reg_idx, chosen_proxy))
        
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error fatal di salah satu tugas: {e}. Bot mungkin perlu di-restart.")

    print_progress()
    logger.info("Semua tugas pendaftaran domain telah selesai!")
    input("Tekan Enter untuk keluar...")

if __name__ == "__main__":
    logging.getLogger(__name__).setLevel(logging.DEBUG) # Mengatur level logger ke DEBUG
    clear_screen()
    logger.info("Bot pendaftar domain dimulai. Pastikan 'accounts.txt' dan 'proxy.txt' (opsional) tersedia.")
    while True:
        try:
            main()
            break
        except Exception as err:
            logger.critical(f"Terjadi error SANGAT FATAL di fungsi utama (main) yang tidak tertangani: {str(err)}")
            logger.info("Menunggu 60 detik sebelum mencoba lagi semua proses...")
            time.sleep(60)
