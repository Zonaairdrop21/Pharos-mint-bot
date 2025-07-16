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
    # 'REG_PER_KEY' dan 'MAX_CONCURRENCY' akan diatur saat runtime
    'CHAIN_ID': 688688  # ID rantai untuk transaksi
}

# ABI minimal untuk kontrak controller (tidak berubah)
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
        # Menyesuaikan agar tidak keluar dari fungsi jika panjang kurang dari 3
        # Biarkan saja dan perbaiki di dalam fungsi
        pass 

    chars_letters = string.ascii_lowercase
    chars_letters_digits = string.ascii_lowercase + string.digits
    
    name_list = []

    # Karakter pertama harus huruf
    name_list.append(random.choice(chars_letters))

    for _ in range(length - 1):
        if name_list[-1] == '-':
            # Setelah tanda hubung harus huruf atau angka
            name_list.append(random.choice(chars_letters_digits))
        else:
            # Bisa huruf, angka, atau tanda hubung (dengan probabilitas lebih tinggi untuk huruf/angka)
            name_list.append(random.choice(chars_letters_digits + '-' * 1)) # '*'1 untuk mengurangi probabilitas '-'

    # Karakter terakhir harus huruf atau angka
    if name_list[-1] == '-':
        name_list[-1] = random.choice(chars_letters_digits)

    # Final check: memastikan tidak ada tanda hubung ganda
    cleaned_name = []
    for i, char in enumerate(name_list):
        if char == '-' and i > 0 and cleaned_name[-1] == '-':
            # Jika ada tanda hubung ganda, ganti yang sekarang
            cleaned_name.append(random.choice(chars_letters_digits))
        else:
            cleaned_name.append(char)
            
    # Pastikan panjang akhir sesuai permintaan
    while len(cleaned_name) < length:
        # Tambahkan karakter acak jika panjangnya berkurang setelah pembersihan
        if cleaned_name and cleaned_name[-1] == '-':
            cleaned_name.append(random.choice(chars_letters_digits))
        else:
            cleaned_name.append(random.choice(chars_letters_digits + '-'))

    return ''.join(cleaned_name[:length]) # Potong jika lebih panjang dari yang diminta

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
processed_lock = threading.Lock() # Untuk mengamankan akses ke current_tasks_processed

def register_domain_task(private_key: str, index: int, reg_index: int, proxy: str = None) -> None:
    """Mendaftarkan domain untuk kunci pribadi tertentu."""
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
    name = "" # Inisialisasi nama di luar loop retry
    while retry < MAX_RETRY:
        try:
            account = Account.from_key(private_key)
            controller = w3.eth.contract(address=controller_address, abi=CONTROLLER_ABI)
            
            owner = account.address
            
            # Buat nama domain baru hanya di percobaan pertama atau jika nama sebelumnya gagal
            if retry == 0 or name == "":
                name = random_name() 
            
            secret = HexBytes(os.urandom(32))
            
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Wallet: {owner}, Nama domain: {name}.phrs")

            # 1. Buat commitment
            # logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Membuat commitment untuk {name}.phrs...")
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
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Commitment dibuat.")

            # 2. Kirim transaksi commit
            # logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Mengirim transaksi commit...")
            tx = controller.functions.commit(commitment).build_transaction({
                'from': owner,
                'nonce': w3.eth.get_transaction_count(owner),
                'gas': 200000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Commitment berhasil. TX Hash: {tx_hash.hex()}")
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Commitment gagal. TX Hash: {tx_hash.hex()}")
                raise Exception("Transaksi commitment gagal.")

            # 3. Tunggu minCommitmentAge (60 detik)
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Menunggu 60 detik...")
            time.sleep(60)

            # 4. Hitung harga sewa domain
            price = controller.functions.rentPrice(name, CONFIG['DURATION']).call()
            value = price[0] + price[1]
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Harga sewa: {w3.from_wei(value, 'ether')} ETH.")

            # 5. Kirim transaksi pendaftaran
            # logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Mengirim transaksi pendaftaran...")
            tx = controller.functions.register(
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
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Pendaftaran {name}.phrs berhasil! TX Hash: {tx_hash.hex()}")
                domain_registered = True
                break
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Pendaftaran {name}.phrs gagal. TX Hash: {tx_hash.hex()}")
                raise Exception("Transaksi pendaftaran gagal.")

        except Exception as err:
            retry += 1
            msg = str(err)[:150] + '...' if len(str(err)) > 150 else str(err)
            if retry < MAX_RETRY:
                logger.warning(f"[Wallet #{index+1} | Percobaan {reg_index}] Error: {msg} - mencoba lagi ({retry}/{MAX_RETRY}) dalam 60 detik...")
                time.sleep(60)
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Gagal mendaftarkan {name}.phrs setelah {MAX_RETRY} percobaan: {msg}")
                
    with processed_lock:
        if domain_registered:
            success_count += 1
        else:
            failed_count += 1
        current_tasks_processed += 1
    
    # Update progress di konsol
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
    # Ini hanya dashboard umum, detail per akun akan tetap di logger

def main():
    """Fungsi utama untuk menjalankan proses pendaftaran domain."""
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
            use_proxy_option = '2' # Otomatis ganti ke mode tanpa proxy
        else:
            logger.info(f"Menguji {len(raw_proxy_list)} proxy yang ditemukan...")
            # Menentukan max_workers untuk pengujian proxy
            proxy_test_workers = min(len(raw_proxy_list), os.cpu_count() * 2 if os.cpu_count() else 10)
            
            # Jika proxy_test_workers bisa 0 (misal raw_proxy_list kosong), ini menyebabkan error.
            # Pastikan minimal 1 jika ada proxy yang akan diuji.
            if proxy_test_workers == 0 and len(raw_proxy_list) > 0:
                 proxy_test_workers = 1 # Minimal 1 worker jika ada proxy untuk diuji

            if proxy_test_workers > 0: # Hanya buat thread pool jika ada worker
                with ThreadPoolExecutor(max_workers=proxy_test_workers) as executor:
                    tested_proxies_results = list(executor.map(test_proxy, raw_proxy_list))
                proxy_list = [p for p, success in tested_proxies_results if success]
            
            if not proxy_list:
                logger.warning("Tidak ada proxy yang berfungsi dari 'proxy.txt'. Bot akan berjalan tanpa proxy.")
                use_proxy_option = '2'
            else:
                logger.info(f"{len(proxy_list)} proxy berfungsi dan akan digunakan.")

    # Memuat kunci pribadi dari accounts.txt
    pk_list = load_file_lines("accounts.txt") # Mengubah dari pk.txt ke accounts.txt
    
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

    # Reset global counters
    success_count = 0
    failed_count = 0
    current_tasks_processed = 0

    # Membangun daftar tugas: (kunci_pribadi, indeks_wallet, indeks_pendaftaran_untuk_wallet_ini)
    tasks = [(pk, idx, i + 1) for idx, pk in enumerate(pk_list) for i in range(CONFIG['REG_PER_KEY'])]
    random.shuffle(tasks) # Acak urutan tugas
    total_tasks = len(tasks)

    print_progress() # Tampilkan dashboard awal

    logger.info(f"Memulai pendaftaran domain untuk {len(pk_list)} akun, total {total_tasks} pendaftaran.")
    
    with ThreadPoolExecutor(max_workers=CONFIG['MAX_CONCURRENCY']) as executor:
        futures = []
        for pk, idx, reg_idx in tasks:
            chosen_proxy = None
            if use_proxy_option == '1' and proxy_list:
                chosen_proxy = random.choice(proxy_list)
            
            futures.append(executor.submit(register_domain_task, pk, idx, reg_idx, chosen_proxy))
        
        # Tunggu semua tugas selesai
        for future in futures:
            future.result() # Mengambil hasil (atau menangani pengecualian)

    print_progress() # Tampilkan dashboard akhir
    logger.info("Semua tugas pendaftaran domain telah selesai!")
    input("Tekan Enter untuk keluar...")

if __name__ == "__main__":
    clear_screen()
    logger.info("Bot pendaftar domain dimulai. Pastikan 'accounts.txt' dan 'proxy.txt' (opsional) tersedia.")
    while True:
        try:
            main()
            break
        except Exception as err:
            logger.error(f"Terjadi error fatal di fungsi utama (main): {str(err)}")
            logger.info("Menunggu 60 detik sebelum mencoba lagi semua proses...")
            time.sleep(60)
