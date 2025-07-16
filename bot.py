import threading
import queue
import random
import time
import os
import string # Tambahan untuk karakter nama domain
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

# Konfigurasi
CONFIG = {
    'RPC_URL': "https://testnet.dplabs-internal.com",
    'CONTROLLER_ADDRESS': "0x51be1ef20a1fd5179419738fc71d95a8b6f8a175",
    'DURATION': 31536000, # Durasi pendaftaran dalam detik (1 tahun)
    'RESOLVER': "0x9a43dcA1C3BB268546b98eb2AB1401bFc5b58505",
    'DATA': [],
    'REVERSE_RECORD': True,
    'OWNER_CONTROLLED_FUSES': 0,
    'REG_PER_KEY': 1, # Berapa kali setiap kunci pribadi akan mendaftar domain
    'MAX_CONCURRENCY': 10, # Jumlah thread maksimum yang berjalan bersamaan
    'CHAIN_ID': 688688  # ID rantai untuk transaksi
}

# ABI minimal untuk kontrak controller
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

def load_file_lines(filename: str) -> List[str]:
    """Memuat baris dari file teks."""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"File {filename} tidak ditemukan. Pastikan file ada di direktori yang sama.")
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
    if length < 3: # Nama domain biasanya minimal 3 karakter
        raise ValueError("Panjang nama domain harus minimal 3 karakter.")

    chars_letters = string.ascii_lowercase
    chars_letters_digits = string.ascii_lowercase + string.digits
    
    name_list = [random.choice(chars_letters)] # Selalu mulai dengan huruf

    for _ in range(length - 2): # Sisa karakter, kecuali yang terakhir
        if name_list[-1] == '-':
            name_list.append(random.choice(chars_letters_digits)) # Setelah tanda hubung harus huruf/angka
        else:
            name_list.append(random.choice(chars_letters_digits + '-'))

    name_list.append(random.choice(chars_letters_digits)) # Karakter terakhir harus huruf/angka
    
    # Perbaikan terakhir untuk memastikan tidak ada tanda hubung ganda atau di ujung
    final_name = []
    for i, char in enumerate(name_list):
        if char == '-':
            # Cegah tanda hubung di awal atau akhir, atau tanda hubung ganda
            if i == 0 or i == len(name_list) - 1 or final_name[-1] == '-':
                # Ganti dengan karakter acak jika tidak memenuhi aturan
                final_name.append(random.choice(chars_letters_digits))
            else:
                final_name.append(char)
        else:
            final_name.append(char)
            
    # Jika hasil akhir kurang dari panjang yang diminta karena koreksi, tambahkan karakter
    while len(final_name) < length:
        final_name.append(random.choice(chars_letters_digits))

    return ''.join(final_name[:length]) # Pastikan panjangnya tetap sesuai permintaan


def test_proxy(proxy: str) -> bool:
    """Menguji apakah proxy berfungsi dengan mencoba koneksi ke api.ipify.org."""
    try:
        response = requests.get('https://api.ipify.org', proxies={'http': proxy, 'https': proxy}, timeout=5)
        return response.status_code == 200
    except (requests.RequestException, HTTPError) as e:
        logger.debug(f"Proxy {proxy} gagal diuji: {e}") # Gunakan debug untuk error proxy yang tidak kritis
        return False

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
    # Kunci pribadi Ethereum harus 64 karakter heksadesimal
    if len(private_key) != 64 or not all(c in string.hexdigits for c in private_key):
        return False
    return True

def register_domain(private_key: str, index: int, reg_index: int, proxy: str = None) -> None:
    """Mendaftarkan domain untuk kunci pribadi tertentu."""
    MAX_RETRY = 5
    retry = 0
    
    if not validate_private_key(private_key):
        logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Kunci pribadi tidak valid, melewati pendaftaran.")
        return

    w3 = create_web3_instance(proxy)
    
    try:
        controller_address = w3.to_checksum_address(CONFIG['CONTROLLER_ADDRESS'])
        resolver_address = w3.to_checksum_address(CONFIG['RESOLVER'])
    except ValueError as e:
        logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Alamat kontrak atau resolver tidak valid dalam konfigurasi: {e}")
        return

    while retry < MAX_RETRY:
        try:
            account = Account.from_key(private_key)
            controller = w3.eth.contract(address=controller_address, abi=CONTROLLER_ABI)
            
            owner = account.address
            name = random_name() # Memanggil fungsi random_name yang sudah diperbarui
            secret = HexBytes(os.urandom(32)) # Secret acak untuk commitment
            
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Wallet: {owner}, Nama domain yang akan didaftarkan: {name}.phrs")

            # 1. Buat commitment
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Membuat commitment untuk {name}.phrs...")
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
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Commitment berhasil dibuat: {commitment.hex()}")

            # 2. Kirim transaksi commit
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Mengirim transaksi commit...")
            tx = controller.functions.commit(commitment).build_transaction({
                'from': owner,
                'nonce': w3.eth.get_transaction_count(owner),
                'gas': 200000, # Gas limit yang cukup
                'gasPrice': w3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Transaksi commitment berhasil! TX Hash: {tx_hash.hex()}")
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Transaksi commitment gagal. TX Hash: {tx_hash.hex()}")
                raise Exception("Transaksi commitment gagal")

            # 3. Tunggu minCommitmentAge (60 detik)
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Menunggu minCommitmentAge (60 detik) sebelum pendaftaran akhir...")
            time.sleep(60)

            # 4. Hitung harga sewa domain
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Menghitung harga sewa untuk {name}.phrs...")
            price = controller.functions.rentPrice(name, CONFIG['DURATION']).call()
            value = price[0] + price[1] # Base price + premium
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Harga sewa: {w3.from_wei(value, 'ether')} ETH")

            # 5. Kirim transaksi pendaftaran
            logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Mengirim transaksi pendaftaran untuk {name}.phrs...")
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
                'nonce': w3.eth.get_transaction_count(owner), # Dapatkan nonce terbaru
                'gas': 300000, # Gas limit yang lebih tinggi untuk pendaftaran
                'gasPrice': w3.eth.gas_price,
                'value': value, # Sertakan nilai ETH untuk pembayaran sewa
                'chainId': CONFIG['CHAIN_ID']
            })
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"[Wallet #{index+1} | Percobaan {reg_index}] Pendaftaran {name}.phrs berhasil! TX Hash: {tx_hash.hex()}")
                break # Berhasil, keluar dari loop retry
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Pendaftaran {name}.phrs gagal. TX Hash: {tx_hash.hex()}")
                raise Exception("Transaksi pendaftaran gagal")

        except Exception as err:
            retry += 1
            msg = str(err)[:150] + '...' if len(str(err)) > 150 else str(err)
            if retry < MAX_RETRY:
                logger.warning(f"[Wallet #{index+1} | Percobaan {reg_index}] Error saat memproses {name}.phrs: {msg} - mencoba lagi ({retry}/{MAX_RETRY}) dalam 60 detik...")
                time.sleep(60)
            else:
                logger.error(f"[Wallet #{index+1} | Percobaan {reg_index}] Gagal mendaftarkan {name}.phrs setelah {MAX_RETRY} percobaan: {msg}")
                break # Gagal setelah semua percobaan

def main():
    """Fungsi utama untuk menjalankan proses pendaftaran domain secara paralel."""
    pk_list = load_file_lines("pk.txt")
    
    # Filter proxy yang aktif
    raw_proxy_list = load_file_lines("proxy.txt")
    logger.info(f"Menguji {len(raw_proxy_list)} proxy yang ditemukan...")
    # Menggunakan ThreadPoolExecutor untuk menguji proxy secara paralel
    with ThreadPoolExecutor(max_workers=min(len(raw_proxy_list), CONFIG['MAX_CONCURRENCY'] * 2)) as executor:
        tested_proxies = list(executor.map(test_proxy, raw_proxy_list))
    proxy_list = [p for p, success in zip(raw_proxy_list, tested_proxies) if success]

    if not pk_list:
        logger.error("Tidak ditemukan kunci pribadi di pk.txt. Pastikan file ada dan berisi kunci pribadi.")
        return
    
    if not proxy_list and raw_proxy_list:
        logger.warning("Tidak ada proxy yang berfungsi dari file proxy.txt. Bot akan berjalan tanpa proxy.")
    elif not raw_proxy_list:
        logger.info("Tidak ada file proxy.txt atau kosong. Bot akan berjalan tanpa proxy.")


    # Membangun daftar tugas: (kunci_pribadi, indeks_wallet, indeks_pendaftaran_untuk_wallet_ini)
    tasks = [(pk, idx, i + 1) for idx, pk in enumerate(pk_list) for i in range(CONFIG['REG_PER_KEY'])]
    random.shuffle(tasks) # Acak urutan tugas

    logger.info(f"Memulai pendaftaran domain untuk {len(pk_list)} wallet, total {len(tasks)} pendaftaran.")
    
    # Gunakan ThreadPoolExecutor untuk menjalankan tugas secara paralel
    with ThreadPoolExecutor(max_workers=CONFIG['MAX_CONCURRENCY']) as executor:
        futures = []
        for pk, idx, reg_idx in tasks:
            # Pilih proxy acak jika ada
            chosen_proxy = random.choice(proxy_list) if proxy_list else None
            futures.append(executor.submit(register_domain, pk, idx, reg_idx, chosen_proxy))
        
        # Tunggu semua tugas selesai
        for future in futures:
            future.result() # Mengambil hasil (atau menangani pengecualian)

    logger.info("Semua tugas pendaftaran domain telah selesai!")

if __name__ == "__main__":
    logger.info("Bot pendaftar domain dimulai. Pastikan pk.txt dan proxy.txt (opsional) tersedia.")
    while True:
        try:
            main()
            break # Keluar dari loop setelah main() selesai tanpa error kritis
        except Exception as err:
            logger.error(f"Terjadi error serius di fungsi utama (main): {str(err)}")
            logger.info("Menunggu 60 detik sebelum mencoba lagi semua proses...")
            time.sleep(60)
