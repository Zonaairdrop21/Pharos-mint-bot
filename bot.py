import os
import random
import string
import asyncio
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from fake_useragent import FakeUserAgent
from web3 import Web3
from web3.middleware import geth_poa_middleware
import aiohttp

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
    def action(msg): Logger.log("ACTION", "↪️", msg, Colors.CYAN)
    @staticmethod
    def actionSuccess(msg): Logger.log("ACTION", "✅", msg, Colors.GREEN)

logger = Logger()

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def display_welcome_screen():
    clear_console()
    now = datetime.now()
    print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}")
    print("  ╔══════════════════════════════════════╗")
    print("  ║           D Z A P   B O T            ║")
    print("  ║                                      ║")
    print(f"  ║     {Colors.YELLOW}{now.strftime('%H:%M:%S %d.%m.%Y')}{Colors.BRIGHT_GREEN}           ║")
    print("  ║                                      ║")
    print("  ║     MONAD TESTNET AUTOMATION         ║")
    print(f"  ║   {Colors.BRIGHT_WHITE}ZonaAirdrop{Colors.BRIGHT_GREEN}  |  t.me/ZonaAirdr0p   ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    await asyncio.sleep(1)

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
        self.Router = "0xd17512b7ec12880bd94eca9d774089ff89805f02"
        self.proxies = []
        self.use_proxy = False
        self.accounts = []
        
        self.contract_abi = [
            {"inputs":[],"name":"InvalidInitialization","type":"error"},
            {"inputs":[],"name":"NotInitializing","type":"error"},
            {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},
            {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
            {"inputs":[],"name":"ReentrancyGuardReentrantCall","type":"error"},
            {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"recipient","type":"address"},{"indexed":false,"internalType":"uint64","name":"claimTime","type":"uint64"},{"indexed":false,"internalType":"string","name":"idSource","type":"string"},{"indexed":false,"internalType":"string","name":"id","type":"string"},{"indexed":false,"internalType":"address","name":"tipper","type":"address"},{"indexed":false,"internalType":"address","name":"tokenAddr","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint64","name":"tipTime","type":"uint64"},{"indexed":false,"internalType":"uint32","name":"tokenType","type":"uint32"},{"indexed":false,"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"name":"ClaimEvent","type":"event"},
            {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint64","name":"version","type":"uint64"}],"name":"Initialized","type":"event"},
            {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},
            {"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"idSource","type":"string"},{"indexed":false,"internalType":"string","name":"id","type":"string"},{"indexed":false,"internalType":"address","name":"tipper","type":"address"},{"indexed":false,"internalType":"address","name":"tokenAddr","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint64","name":"tipTime","type":"uint64"},{"indexed":false,"internalType":"uint32","name":"tokenType","type":"uint32"},{"indexed":false,"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"name":"TipEvent","type":"event"},
            {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint64","name":"withdrawTime","type":"uint64"},{"indexed":false,"internalType":"string","name":"idSource","type":"string"},{"indexed":false,"internalType":"string","name":"id","type":"string"},{"indexed":false,"internalType":"address","name":"tipper","type":"address"},{"indexed":false,"internalType":"address","name":"tokenAddr","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint64","name":"tipTime","type":"uint64"},{"indexed":false,"internalType":"uint32","name":"tokenType","type":"uint32"},{"indexed":false,"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"name":"WithdrawEvent","type":"event"},
            {"inputs":[{"internalType":"string[]","name":"sourceName_","type":"string[]"},{"internalType":"string[]","name":"url_","type":"string[]"},{"internalType":"string[]","name":"jsonPath_","type":"string[]"}],"name":"addBatchIdSource","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"string[]","name":"idSources","type":"string[]"},{"components":[{"internalType":"address","name":"recipient","type":"address"},{"components":[{"internalType":"string","name":"url","type":"string"},{"internalType":"string","name":"header","type":"string"},{"internalType":"string","name":"method","type":"string"},{"internalType":"string","name":"body","type":"string"}],"internalType":"struct AttNetworkRequest","name":"request","type":"tuple"},{"components":[{"internalType":"string","name":"keyName","type":"string"},{"internalType":"string","name":"parseType","type":"string"},{"internalType":"string","name":"parsePath","type":"string"}],"internalType":"struct AttNetworkResponseResolve[]","name":"reponseResolve","type":"tuple[]"},{"internalType":"string","name":"data","type":"string"},{"internalType":"string","name":"attConditions","type":"string"},{"internalType":"uint64","name":"timestamp","type":"uint64"},{"internalType":"string","name":"additionParams","type":"string"},{"components":[{"internalType":"address","name":"attestorAddr","type":"address"},{"internalType":"string","name":"url","type":"string"}],"internalType":"struct Attestor[]","name":"attestors","type":"tuple[]"},{"internalType":"bytes[]","name":"signatures","type":"bytes[]"}],"internalType":"struct Attestation[]","name":"att","type":"tuple[]"}],"name":"claimByMultiSource","outputs":[],"stateMutability":"payable","type":"function"},
            {"inputs":[{"internalType":"string","name":"idSource","type":"string"},{"components":[{"internalType":"address","name":"recipient","type":"address"},{"components":[{"internalType":"string","name":"url","type":"string"},{"internalType":"string","name":"header","type":"string"},{"internalType":"string","name":"method","type":"string"},{"internalType":"string","name":"body","type":"string"}],"internalType":"struct AttNetworkRequest","name":"request","type":"tuple"},{"components":[{"internalType":"string","name":"keyName","type":"string"},{"internalType":"string","name":"parseType","type":"string"},{"internalType":"string","name":"parsePath","type":"string"}],"internalType":"struct AttNetworkResponseResolve[]","name":"reponseResolve","type":"tuple[]"},{"internalType":"string","name":"data","type":"string"},{"internalType":"string","name":"attConditions","type":"string"},{"internalType":"uint64","name":"timestamp","type":"uint64"},{"internalType":"string","name":"additionParams","type":"string"},{"components":[{"internalType":"address","name":"attestorAddr","type":"address"},{"internalType":"string","name":"url","type":"string"}],"internalType":"struct Attestor[]","name":"attestors","type":"tuple[]"},{"internalType":"bytes[]","name":"signatures","type":"bytes[]"}],"internalType":"struct Attestation","name":"att","type":"tuple"}],"name":"claimBySource","outputs":[],"stateMutability":"payable","type":"function"},
            {"inputs":[],"name":"claimFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"feeRecipient","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"components":[{"internalType":"string","name":"idSource","type":"string"},{"internalType":"string","name":"id","type":"string"}],"internalType":"struct TipRecipient","name":"tipRecipient","type":"tuple"}],"name":"getTipRecords","outputs":[{"components":[{"internalType":"uint256","name":"amount","type":"uint256"},{"components":[{"internalType":"uint32","name":"tokenType","name":"uint32"},{"internalType":"address","name":"tokenAddress","type":"address"}],"internalType":"struct TipToken","name":"tipToken","type":"tuple"},{"internalType":"uint64","name":"timestamp","type":"uint64"},{"internalType":"address","name":"tipper","type":"address"},{"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"internalType":"struct TipRecord[]","name":"","type":"tuple[]"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"string","name":"","type":"string"}],"name":"idSourceCache","outputs":[{"internalType":"string","name":"url","type":"string"},{"internalType":"string","name":"jsonPath","type":"string"}],"stateMutability":"view","type":"function"},
            {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"contract IPrimusZKTLS","name":"primusZKTLS_","type":"address"},{"internalType":"address","name":"feeRecipient_","type":"address"},{"internalType":"uint256","name":"claimFee_","type":"uint256"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"primusZKTLS","outputs":[{"internalType":"contract IPrimusZKTLS","name":"","type":"address"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"claimFee_","type":"uint256"}],"name":"setClaimFee","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"address","name":"feeRecipient_","type":"address"}],"name":"setFeeRecipient","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"contract IPrimusZKTLS","name":"primusZKTLS_","type":"address"}],"name":"setPrimusZKTLS","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"uint256","name":"delay","type":"uint256"}],"name":"setWithdrawDelay","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"components":[{"internalType":"uint32","name":"tokenType","type":"uint32"},{"internalType":"address","name":"tokenAddress","type":"address"}],"internalType":"struct TipToken","name":"token","type":"tuple"},{"components":[{"internalType":"string","name":"idSource","type":"string"},{"internalType":"string","name":"id","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"internalType":"struct TipRecipientInfo","name":"recipient","type":"tuple"}],"name":"tip","outputs":[],"stateMutability":"payable","type":"function"},
            {"inputs":[{"components":[{"internalType":"uint32","name":"tokenType","type":"uint32"},{"internalType":"address","name":"tokenAddress","type":"address"}],"internalType":"struct TipToken","name":"token","type":"tuple"},{"components":[{"internalType":"string","name":"idSource","type":"string"},{"internalType":"string","name":"id","type":"string"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256[]","name":"nftIds","type":"uint256[]"}],"internalType":"struct TipRecipientInfo[]","name":"recipients","type":"tuple[]"}],"name":"tipBatch","outputs":[],"stateMutability":"payable","type":"function"},
            {"inputs":[{"components":[{"internalType":"string","name":"idSource","type":"string"},{"internalType":"string","name":"id","type":"string"},{"internalType":"uint64","name":"tipTimestamp","type":"uint64"}],"internalType":"struct TipWithdrawInfo[]","name":"tipRecipients","type":"tuple[]"}],"name":"tipperWithdraw","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
            {"inputs":[],"name":"withdrawDelay","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
        ]
        
        self.init_web3()
        
        self.load_accounts()
        self.load_proxies()

    def init_web3(self, proxy=None):
        if proxy:
            logger.warn("Proxy integration for Web3 RPC is complex with standard HTTPProvider. Ensure system proxy is set if needed.")
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        else:
            self.w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract = self.w3.eth.contract(
            address=self.Router,
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
                            logger.error(f"Invalid private key: {line[:6]}...{line[-4:]}")
            logger.success(f"Loaded {len(self.accounts)} accounts")
            if not self.accounts:
                logger.error("No valid accounts found in accounts.txt. Please add private keys.")
                exit()
        except FileNotFoundError:
            logger.error("accounts.txt file not found! Please create it and add private keys.")
            exit()

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.proxies.append(line)
            logger.success(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            logger.warn("proxies.txt file not found - running without proxies by default. Use option 3 to enable proxy mode if proxies are added later.")

    def generate_random_username(self, platform='x'):
        prefix = '@'
        length = random.randint(5, 12)
        chars = string.ascii_lowercase + string.digits + '_'
        return prefix + ''.join(random.choice(chars) for _ bathed(length))

    async def check_balance(self, account):
        try:
            balance = self.w3.eth.get_balance(account.address)
            return {
                'eth': self.w3.from_wei(balance, 'ether'),
                'token': "N/A (No ERC20 balanceOf in Router ABI)"
            }
        except Exception as e:
            logger.error(f"Balance check failed for {account.address}: {str(e)}")
            return None

    async def send_tip(self, sender_account, username, amount):
        try:
            tip_token = {
                "tokenType": 1,
                "tokenAddress": self.Router
            }
            
            tip_recipient = {
                "idSource": "x",
                "id": username,
                "amount": self.w3.to_wei(amount, 'ether'),
                "nftIds": []
            }
            
            tx = self.contract.functions.tip(
                tip_token,
                tip_recipient
            ).build_transaction({
                'from': sender_account.address,
                'nonce': self.w3.eth.get_transaction_count(sender_account.address),
                'gas': 300000,
                'gasPrice': self.w3.to_wei('50', 'gwei'),
                'value': 0
            })
            
            signed_tx = sender_account.sign_transaction(tx)
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.actionSuccess(f"Sent {amount} of token (at {self.Router}) to {username} | TX: {tx_hash.hex()}")
                return True
            else:
                logger.error(f"Transaction failed for {username}. Receipt status: {receipt.status}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending tip from {sender_account.address} to {username}: {str(e)}")
            return False

    async def show_menu(self):
        clear_console()
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== DZAP BOT MENU ===")
        print(f"{Colors.RESET}")
        print("1. Run Automated Tip Cycle (24 hours)")
        print("2. Check Balances")
        print("3. Run Single Tip (Manual)")
        print("4. Enable/Disable Proxy Mode")
        print("5. Exit")
        
        choice = input(f"\n{Colors.CYAN}Select option (1-5): {Colors.RESET}")
        return choice

    async def send_single_tip_menu(self):
        clear_console()
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== SEND SINGLE TIP ===")
        print(f"{Colors.RESET}")
        
        if not self.accounts:
            logger.error("No accounts available!")
            return
            
        print("\nAvailable Accounts:")
        for i, acc in enumerate(self.accounts, 1):
            print(f"{i}. {acc.address}")
            
        acc_choice = input(f"\n{Colors.CYAN}Select account (1-{len(self.accounts)}): {Colors.RESET}")
        try:
            account = self.accounts[int(acc_choice)-1]
        except (ValueError, IndexError):
            logger.error("Invalid selection! Please enter a valid number.")
            return
            
        amount_str = input(f"\n{Colors.CYAN}How much do you want to send? {Colors.RESET}")
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            logger.error("Invalid amount! Please enter a positive number.")
            return
            
        username = self.generate_random_username()
        
        print(f"\n{Colors.YELLOW}Ready to send {amount} (token at {self.Router}) to {username}")
        confirm = input(f"{Colors.CYAN}Confirm? (y/n): {Colors.RESET}")
        if confirm.lower() != 'y':
            logger.info("Tip cancelled.")
            return
            
        logger.action(f"Sending {amount} to {username} from {account.address}...")
        success = await self.send_tip(account, username, amount)
        if success:
            logger.success("Single tip sent successfully!")
        else:
            logger.error("Failed to send single tip!")
            
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")

    async def check_balances(self):
        clear_console()
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}=== ACCOUNT BALANCES ===")
        print(f"{Colors.RESET}")
        
        if not self.accounts:
            logger.error("No accounts available!")
            return
            
        for account in self.accounts:
            balances = await self.check_balance(account)
            if balances:
                print(f"\n{Colors.CYAN}Account: {account.address}")
                print(f"{Colors.WHITE}ETH Balance: {balances['eth']}")
                print(f"{Colors.WHITE}Token Balance: {balances['token']}")
            else:
                logger.error(f"Failed to check balance for {account.address}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")

    async def countdown(self, seconds):
        while seconds > 0:
            minutes, secs = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            timer = f"{hours:02d}:{minutes:02d}:{secs:02d}"
            print(f"\r{Colors.YELLOW}Next run in: {timer}{Colors.RESET}", end="")
            await asyncio.sleep(1)
            seconds -= 1
        print("\r" + " " * 50 + "\r", end="")

    async def automated_tip_cycle(self):
        logger.info("Starting automated tip cycle (24-hour interval)...")
        while True:
            for account in self.accounts:
                clear_console()
                logger.step(f"Processing account: {account.address}")
                
                balances = await self.check_balance(account)
                if balances:
                    logger.info(f"Current ETH Balance: {balances['eth']}")
                else:
                    logger.warn(f"Could not retrieve balance for {account.address}. Skipping this account for now.")
                    continue

                amount_to_send = 0.0001

                username = self.generate_random_username()

                logger.action(f"Attempting to send {amount_to_send} (token at {self.Router}) to {username} from {account.address}...")
                success = await self.send_tip(account, username, amount_to_send)
                if success:
                    logger.success(f"Successfully tipped {amount_to_send} to {username} from {account.address}.")
                else:
                    logger.error(f"Failed to tip {amount_to_send} to {username} from {account.address}.")
                
                await asyncio.sleep(5)

            logger.info("All accounts processed for this cycle. Waiting for next cycle...")
            await self.countdown(24 * 60 * 60)
            logger.info("24-hour delay complete. Starting next automated tip cycle.")


    async def run(self):
        await display_welcome_screen()
        
        while True:
            choice = await self.show_menu()
            
            if choice == '1':
                await self.automated_tip_cycle()
            elif choice == '2':
                await self.check_balances()
            elif choice == '3':
                await self.send_single_tip_menu()
            elif choice == '4':
                self.use_proxy = not self.use_proxy
                if self.use_proxy:
                    logger.success("Proxy mode enabled. (Note: Web3 RPC proxying needs system-level setup or advanced aiohttp integration for AsyncHTTPProvider.)")
                else:
                    logger.success("Proxy mode disabled.")
                await asyncio.sleep(1)
            elif choice == '5':
                logger.info("Exiting...")
                break
            else:
                logger.error("Invalid choice!")
                await asyncio.sleep(1)

if __name__ == "__main__":
    bot = SocialTipBot()
    asyncio.run(bot.run())
