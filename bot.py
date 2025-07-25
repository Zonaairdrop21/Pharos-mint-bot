import os
import random
import string
import asyncio
from datetime import datetime
from colorama import Fore, Style, init
from fake_useragent import FakeUserAgent
from web3 import Web3
# from web3.middleware.geth import geth_poa_middleware # Baris ini tetap dikomentari sesuai permintaan
import aiohttp # aiohttp tetap diperlukan untuk potential future async HTTP requests jika tidak menggunakan Web3's built-in async

init(autoreset=True)

class Colors:
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    BRIGHT_GREEN = Fore.LIGHTGREEN_EX
    BRIGHT_MAGENTA = Fore.LIGHTMAGENTA_EX
    BRIGHT_WHITE = Fore.LIGHTWHITE_EX
    BRIGHT_BLACK = Fore.LIGHTBLACK_EX

class Logger:
    @staticmethod
    def log(label, symbol, msg, color):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.BRIGHT_BLACK}[{timestamp}]{Colors.RESET} {color}[{symbol}] {msg}{Colors.RESET}")

    @staticmethod
    def info(msg): Logger.log("INFO", "✓", msg, Colors.GREEN)
    @staticmethod
    def warn(msg): Logger.log("WARN", "!", msg, Colors.YELLOW)
    @staticmethod
    def error(msg): Logger.log("ERR", "✗", msg, Colors.RED)
    @staticmethod
    def success(msg): Logger.log("OK", "+", msg, Colors.GREEN)
    @staticmethod
    def loading(msg): Logger.log("LOAD", "⟳", msg, Colors.CYAN)
    @staticmethod
    def step(msg): Logger.log("STEP", "➤", msg, Colors.WHITE)
    @staticmethod
    def action(msg): Logger.log("ACTION", "↪️", msg, Colors.CYAN) # For transaction initiation
    @staticmethod
    def actionSuccess(msg): Logger.log("ACTION", "✅", msg, Colors.GREEN) # For transaction success with explorer link

logger = Logger()

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def display_welcome_screen():
    # clear_console() # Hapus baris ini agar menu tidak berpindah layar
    now = datetime.now()
    print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}")
    print("  ╔══════════════════════════════════════╗")
    print("  ║            D Z A P  B O T            ║")
    print("  ║                                      ║")
    print(f"  ║      {Colors.YELLOW}{now.strftime('%H:%M:%S %d.%m.%Y')}{Colors.BRIGHT_GREEN}            ║")
    print("  ║                                      ║")
    print("  ║      PHAROS TESTNET AUTOMATION       ║")
    print(f"  ║   {Colors.BRIGHT_WHITE}ZonaAirdrop{Colors.BRIGHT_GREEN}  |  t.me/ZonaAirdr0p    ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    # await asyncio.sleep(1) # Hapus atau kurangi waktu sleep jika ingin instant menu

class SocialTipBot:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://pay.primuslabs.xyz/",
            "Referer": "https://pay.primuslabs.xyz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://api.pharosnetwork.xyz"
        self.RPC_URL = "https://testnet.dplabs-internal.com"
        self.Explorer_URL = "https://explorer.dplabs-internal.com/tx/" # Example explorer URL, adjust if different
        self.Router = "0xd17512b7ec12880bd94eca9d774089ff89805f02" # This address will be converted to checksum
        self.proxies = []
        self.use_proxy = False
        self.accounts = []
        self.min_delay = 0
        self.max_delay = 0
        
        # ABI, only contains "tip" method with corrected booleans
        self.contract_abi = [
            {
                "inputs": [
                    {
                        "components": [
                            {
                                "internalType": "uint32",
                                "name": "tokenType",
                                "type": "uint32"
                            },
                            {
                                "internalType": "address",
                                "name": "tokenAddress",
                                "type": "address"
                            }
                        ],
                        "internalType": "struct TipToken",
                        "name": "token",
                        "type": "tuple"
                    },
                    {
                        "components": [
                            {
                                "internalType": "string",
                                "name": "idSource",
                                "type": "string"
                            },
                            {
                                "internalType": "string",
                                "name": "id",
                                "type": "string"
                            },
                            {
                                "internalType": "uint256",
                                "name": "amount",
                                "type": "uint256"
                            },
                            {
                                "internalType": "uint256[]",
                                "name": "nftIds",
                                "type": "uint256[]"
                            }
                        ],
                        "internalType": "struct TipRecipientInfo",
                        "name": "recipient",
                        "type": "tuple"
                    }
                ],
                "name": "tip",
                "outputs": [],
                "stateMutability": "payable", # Crucial for sending native token as value
                "type": "function"
            }
        ]
        
        self.init_web3()
        
        self.load_accounts()
        self.load_proxies()

    def init_web3(self, proxy=None):
        if proxy:
            logger.warn("Integrating proxy for Web3 RPC is complex with standard HTTPProvider. Consider system-wide proxy or custom transport for RPC if truly needed.")
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        else:
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        
        # # Inject PoA middleware if your chain requires it (e.g., Geth PoA) - Baris ini tetap dikomentari
        # try:
        #     self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        # except Exception as e:
        #     logger.warn(f"Could not inject geth_poa_middleware. If your network is not PoA, this is fine. Error: {e}")
        
        self.checksum_router_address = self.w3.to_checksum_address(self.Router)
        
        self.contract = self.w3.eth.contract(
            address=self.checksum_router_address,
            abi=self.contract_abi
        )

    def load_accounts(self):
        try:
            with open('accounts.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            account = self.w3.eth.account.from_key(line)
                            self.accounts.append(account)
                        except ValueError:
                            logger.error(f"Kunci pribadi tidak valid: {line[:6]}...{line[-4:]}")
            logger.success(f"Memuat {len(self.accounts)} akun")
            if not self.accounts:
                logger.error("Tidak ada akun valid yang ditemukan di accounts.txt. Harap tambahkan kunci pribadi.")
                exit()
        except FileNotFoundError:
            logger.error("File accounts.txt tidak ditemukan! Harap buat dan tambahkan kunci pribadi.")
            exit()

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(line)
            logger.success(f"Memuat {len(self.proxies)} proxy")
        except FileNotFoundError:
            logger.warn("File proxies.txt tidak ditemukan - berjalan tanpa proxy secara default. Gunakan opsi 1 untuk mengaktifkan mode proxy jika proxy ditambahkan nanti.")

    def generate_random_username(self, platform='x'):
        prefix = '@'
        length = random.randint(5, 12)
        chars = string.ascii_lowercase + string.digits + '_'
        return prefix + ''.join(random.choice(chars) for _ in range(length))

    async def check_balance(self, account):
        try:
            balance = await asyncio.to_thread(self.w3.eth.get_balance, account.address)
            return {
                'eth': self.w3.from_wei(balance, 'ether'),
                'token': "Tidak Tersedia (Perlu ABI Token spesifik untuk cek saldo ERC20)"
            }
        except Exception as e:
            logger.error(f"Pengecekan saldo gagal untuk {account.address}: {str(e)}")
            return None

    async def send_tip(self, sender_account, username, amount):
        try:
            tip_token = {
                "tokenType": 1, # Assuming 1 for native token (ETH/Pharos token)
                "tokenAddress": "0x0000000000000000000000000000000000000000" # Zero address for native token
            }
            
            value_in_wei = self.w3.to_wei(amount, 'ether')

            tip_recipient = {
                "idSource": "x",
                "id": username,
                "amount": value_in_wei, # This amount for the contract's internal logic
                "nftIds": []
            }
            
            nonce = await asyncio.to_thread(self.w3.eth.get_transaction_count, sender_account.address)

            tx = self.contract.functions.tip(
                tip_token,
                tip_recipient
            ).build_transaction({
                'from': sender_account.address,
                'nonce': nonce,
                'gas': 300000, # Consider fetching gas_limit estimate_gas
                'gasPrice': self.w3.to_wei('50', 'gwei'), # Consider fetching current gas price
                'value': value_in_wei # Crucial: send native token here
            })
            
            signed_tx = sender_account.sign_transaction(tx) 
            
            # PERUBAHAN KRUSIAL DI SINI: Menggunakan .raw_transaction (snake_case)
            raw_transaction = signed_tx.raw_transaction
            # tx_hash_from_signed = signed_tx.hash # Ini juga bisa digunakan jika diperlukan

            logger.action(f"Mengirim transaksi dari {sender_account.address[:6]}...{sender_account.address[-4:]}...")
            
            tx_hash = await asyncio.to_thread(self.w3.eth.send_raw_transaction, raw_transaction)
            
            logger.loading(f"Menunggu konfirmasi transaksi... {self.Explorer_URL}{tx_hash.hex()}")
            
            receipt = await asyncio.to_thread(self.w3.eth.wait_for_transaction_receipt, tx_hash)
            
            if receipt.status == 1:
                explorer_link = f"{self.Explorer_URL}{tx_hash.hex()}"
                logger.actionSuccess(f"Mengirim {amount} token ke {username} | TX: {tx_hash.hex()} | Explorer: {explorer_link}")
                return True
            else:
                logger.error(f"Transaksi gagal untuk {username}. Status tanda terima: {receipt.status}")
                return False
                
        except Exception as e:
            logger.error(f"Error mengirim tip dari {sender_account.address[:6]}...{sender_account.address[-4:]} ke {username}: {str(e)}")
            return False

    async def show_main_menu(self):
        # clear_console() # Hapus baris ini agar menu tidak membersihkan konsol
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== DZAP BOT MENU ===")
        print(f"{Colors.RESET}")
        print("1. Kirim Tip")
        print("2. Cek Saldo")
        print("3. Keluar")
        
        choice = input(f"\n{Colors.CYAN}Pilih opsi (1-3): {Colors.RESET}")
        return choice

    async def show_proxy_menu(self):
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== MODE PROXY ===")
        print(f"{Colors.RESET}")
        print("1. Jalankan dengan proxy pribadi")
        print("2. Jalankan tanpa proxy")
        
        choice = input(f"\n{Colors.CYAN}Pilih opsi (1-2): {Colors.RESET}")
        return choice

    async def handle_send_tip(self):
        clear_console() # Tetap bersihkan konsol saat masuk ke sub-menu
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== KIRIM TIP ===")
        print(f"{Colors.RESET}")
        
        if not self.accounts:
            logger.error("Tidak ada akun yang tersedia! Harap tambahkan kunci pribadi ke accounts.txt.")
            await asyncio.sleep(2)
            return
            
        amount_range_str = input(f"\n{Colors.CYAN}Masukkan rentang jumlah yang ingin dikirim (misal: 0.01-0.05): {Colors.RESET}")
        try:
            min_amount_str, max_amount_str = amount_range_str.split('-')
            min_amount = float(min_amount_str.strip())
            max_amount = float(max_amount_str.strip())
            if min_amount <= 0 or max_amount <= 0 or min_amount > max_amount:
                raise ValueError
            
        except ValueError:
            logger.error("Rentang jumlah tidak valid! Harap masukkan format 'min-max' dengan angka positif (misal: 0.01-0.05).")
            await asyncio.sleep(2)
            return

        if self.proxies:
            proxy_choice = await self.show_proxy_menu()
            if proxy_choice == '1':
                self.use_proxy = True
                logger.info("Mode proxy diaktifkan.")
            elif proxy_choice == '2':
                self.use_proxy = False
                logger.info("Mode proxy dinonaktifkan.")
            else:
                logger.error("Pilihan tidak valid! Membatalkan.")
                await asyncio.sleep(1)
                return
        else:
            logger.warn("Tidak ada file proxies.txt ditemukan, melanjutkan tanpa proxy.")
            self.use_proxy = False

        # Input untuk Min Delay dan Max Delay
        try:
            min_delay_str = input(f"\n{Colors.CYAN}Masukkan delay minimum antar transaksi (detik): {Colors.RESET}")
            self.min_delay = int(min_delay_str.strip())
            max_delay_str = input(f"{Colors.CYAN}Masukkan delay maksimum antar transaksi (detik): {Colors.RESET}")
            self.max_delay = int(max_delay_str.strip())
            if self.min_delay < 0 or self.max_delay < 0 or self.min_delay > self.max_delay:
                raise ValueError
            logger.info(f"Delay antar transaksi diatur antara {self.min_delay}-{self.max_delay} detik.")
        except ValueError:
            logger.error("Delay tidak valid! Harap masukkan angka bulat positif.")
            await asyncio.sleep(2)
            return

        print("\nAkun yang Tersedia:")
        for i, acc in enumerate(self.accounts, 1):
            print(f"{i}. {acc.address}")
            
        acc_choice = input(f"\n{Colors.CYAN}Pilih akun (1-{len(self.accounts)}) atau 'all' untuk semua akun: {Colors.RESET}")
        
        selected_accounts = []
        if acc_choice.lower() == 'all':
            selected_accounts = self.accounts
            logger.info(f"Semua {len(selected_accounts)} akun dipilih.")
        else:
            try:
                account = self.accounts[int(acc_choice)-1]
                selected_accounts.append(account)
                logger.info(f"Akun {account.address} dipilih.")
            except (ValueError, IndexError):
                logger.error("Pilihan tidak valid! Harap masukkan angka yang valid atau 'all'.")
                await asyncio.sleep(2)
                return
        
        for account in selected_accounts:
            amount_to_send = random.uniform(min_amount, max_amount)
            username = self.generate_random_username()
            
            logger.step(f"Mencoba mengirim {amount_to_send:.6f} token (di Router: {self.checksum_router_address}) ke @{username} dari {account.address}...")
            
            selected_proxy = None
            if self.use_proxy and self.proxies:
                selected_proxy = random.choice(self.proxies)
                logger.info(f"Menggunakan proxy: {selected_proxy}")
                logger.warn("Pengaturan proxy untuk panggilan Web3.py RPC memerlukan konfigurasi yang lebih lanjut (misalnya, transport kustom). Proxy yang dipilih dicatat tetapi tidak langsung diterapkan pada transaksi blockchain dalam pengaturan ini.")

            success = await self.send_tip(account, username, amount_to_send)
            if success:
                logger.success("Tip berhasil dikirim!")
            else:
                logger.error("Gagal mengirim tip!")
            
            if len(selected_accounts) > 1: # Apply delay only if multiple accounts are being processed
                delay = random.randint(self.min_delay, self.max_delay)
                logger.loading(f"Menunggu {delay} detik sebelum akun berikutnya...")
                await asyncio.sleep(delay)
            
        input(f"\n{Colors.CYAN}Tekan Enter untuk melanjutkan...{Colors.RESET}")

    async def check_balances_menu(self):
        clear_console()
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== SALDO AKUN ===")
        print(f"{Colors.RESET}")
        
        if not self.accounts:
            logger.error("Tidak ada akun yang tersedia!")
            await asyncio.sleep(2)
            return
            
        for account in self.accounts:
            balances = await self.check_balance(account)
            if balances:
                print(f"\n{Colors.CYAN}Akun: {account.address}")
                print(f"{Colors.WHITE}Saldo ETH: {balances['eth']:.6f}")
                print(f"{Colors.WHITE}Saldo Token: {balances['token']}")
            else:
                logger.error(f"Gagal memeriksa saldo untuk {account.address}")
        
        input(f"\n{Colors.CYAN}Tekan Enter untuk melanjutkan...{Colors.RESET}")

    async def run(self):
        await display_welcome_screen() # Display welcome once
        
        while True:
            # Tidak membersihkan konsol di sini agar menu utama tetap di bawah welcome screen
            choice = await self.show_main_menu() # Always return to main menu
            
            if choice == '1':
                await self.handle_send_tip()
            elif choice == '2':
                await self.check_balances_menu()
            elif choice == '3':
                logger.info("Keluar...")
                break
            else:
                logger.error("Pilihan tidak valid!")
                await asyncio.sleep(1)

if __name__ == "__main__":
    bot = SocialTipBot()
    asyncio.run(bot.run())
