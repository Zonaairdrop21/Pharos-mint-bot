from web3 import Web3
from eth_utils import to_hex
from eth_account import Account
from eth_account.messages import encode_defunct
from aiohttp import ClientResponseError, ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import *
import asyncio, random, secrets, json, time, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class PharosTestnet:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://api.pharosnetwork.xyz"
        self.RPC_URL = "https://testnet.dplabs-internal.com"
        self.WPHRS_CONTRACT_ADDRESS = "0x76aaaDA469D23216bE5f7C596fA25F282Ff9b364"
        self.MINT_CONTRACT_ABI = [
            {
                "inputs": [
                    { "internalType": "address", "name": "_asset", "type": "address" },
                    { "internalType": "address", "name": "_account", "type": "address" },
                    { "internalType": "uint256", "name": "_amount", "type": "uint256" }
                ],
                "name": "mint",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        self.ref_code = "8G8MJ3zGE5B7tJgP" # U can change it with yours.
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.signatures = {}
        self.access_tokens = {}
        self.min_delay = 0
        self.max_delay = 0

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "\n" + "═" * 60)
        print(Fore.GREEN + Style.BRIGHT + "    ⚡ Pharos X Zenith Tesnet ⚡")
        print(Fore.CYAN + Style.BRIGHT + "    ────────────────────────────────")
        print(Fore.YELLOW + Style.BRIGHT + "    Team : Zonaairdrop")
        print(Fore.CYAN + Style.BRIGHT + "    ────────────────────────────────")
        print(Fore.RED + Style.BRIGHT + "   Channel telegram : @ZonaAirdr0p")
        print(Fore.CYAN + Style.BRIGHT + "    ────────────────────────────────")
        print(Fore.MAGENTA + Style.BRIGHT + "   Powered by Zonaairdrop")
        print(Fore.LIGHTGREEN_EX + Style.BRIGHT + "═" * 60 + "\n")
        
    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_proxies(self, use_proxy_choice: int):
        filename = "proxy.txt"
        try:
            if use_proxy_choice == 1: # Scrape from proxyscrape.com
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = [line.strip() for line in content.splitlines() if line.strip()]
            else: # Use proxy.txt
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                    return
                with open(filename, 'r') as f:
                    self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, token):
        if token not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[token] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[token]

    def rotate_proxy_for_account(self, token):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[token] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def generate_address(self, account: str):
        try:
            account = Account.from_key(account)
            address = account.address
            
            return address
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Generate Address Failed {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        
    def generate_signature(self, account: str):
        try:
            encoded_message = encode_defunct(text="pharos")
            signed_message = Account.sign_message(encoded_message, private_key=account)
            signature = to_hex(signed_message.signature)

            return signature
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Generate Signature Failed {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        
    def mask_account(self, account):
        try:
            mask_account = account[:6] + '*' * 6 + account[-6:]
            return mask_account
        except Exception as e:
            return None
        
    async def get_web3_with_check(self, address: str, use_proxy: bool, retries=3, timeout=60):
        request_kwargs = {"timeout": timeout}

        proxy = self.get_next_proxy_for_account(address) if use_proxy else None

        if use_proxy and proxy:
            request_kwargs["proxies"] = {"http": proxy, "https": proxy}

        for attempt in range(retries):
            try:
                web3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs=request_kwargs))
                web3.eth.get_block_number()
                return web3
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(3)
                    continue
                raise Exception(f"Failed to Connect to RPC: {str(e)}")
        
    async def get_access_token(self, account: str, address: str, signature: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        connector = ProxyConnector.from_url(proxy) if proxy else None

        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                data = json.dumps({
                    "address": address,
                    "signature": signature
                })
                async with session.post(f"{self.BASE_API}/auth/login", headers=self.headers, data=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    access_token = result["data"]["accessToken"]
                    
                    self.access_tokens[address] = access_token
                    return access_token
        except ClientResponseError as e:
            if e.status == 400:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Bad Request - Ensure All Parameters Are Correct. {Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed To Get Access Token {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {e.status} {str(e)} {Style.RESET_ALL}                  "
                )
            return None
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Get Access Token {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        finally:
            if connector:
                await connector.close()

    async def get_user_info(self, address: str, access_token: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        connector = ProxyConnector.from_url(proxy) if proxy else None
        
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"

        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(f"{self.BASE_API}/users", headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    return result
        except ClientResponseError as e:
            if e.status == 401:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Invalid Or Expired Access Token. {Style.RESET_ALL}"
                )
                self.access_tokens.pop(address, None)
            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed To Get User Info {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {e.status} {str(e)} {Style.RESET_ALL}                  "
                )
            return None
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Get User Info {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        finally:
            if connector:
                await connector.close()

    async def check_in(self, address: str, access_token: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        connector = ProxyConnector.from_url(proxy) if proxy else None
        
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"
        
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.post(f"{self.BASE_API}/checkin", headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    return result
        except ClientResponseError as e:
            if e.status == 400:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Daily Check-In Already Claimed. {Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed To Perform Check-In {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {e.status} {str(e)} {Style.RESET_ALL}                  "
                )
            return None
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Perform Check-In {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        finally:
            if connector:
                await connector.close()

    async def claim_faucet(self, address: str, access_token: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        connector = ProxyConnector.from_url(proxy) if proxy else None
        
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"
        
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                data = json.dumps({"address": address})
                async with session.post(f"{self.BASE_API}/faucet/claim", headers=headers, data=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    return result
        except ClientResponseError as e:
            if e.status == 400:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} PHRS Faucet Already Claimed Or Limit Reached. {Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed To Claim Faucet {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {e.status} {str(e)} {Style.RESET_ALL}                  "
                )
            return None
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Claim Faucet {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        finally:
            if connector:
                await connector.close()
                
    async def claim_phrs_faucet(self, account: str, address: str, use_proxy: bool):
        try:
            web3 = await self.get_web3_with_check(address, use_proxy)

            contract_address = web3.to_checksum_address("0xC466986F1b3F0f18B51E09460E7132958742C026")
            mint_contract = web3.eth.contract(address=contract_address, abi=self.MINT_CONTRACT_ABI)

            mint_data = mint_contract.functions.mint(
                web3.to_checksum_address(self.WPHRS_CONTRACT_ADDRESS),
                web3.to_checksum_address(address),
                web3.to_wei(1000, "ether")
            )
            
            estimated_gas = mint_data.estimate_gas({"from": address})

            max_priority_fee = web3.to_wei(1, "gwei")
            max_fee = max_priority_fee

            mint_tx = mint_data.build_transaction({
                "from": address,
                "gas": int(estimated_gas * 1.2),
                "maxFeePerGas": int(max_fee),
                "maxPriorityFeePerGas": int(max_priority_fee),
                "nonce": web3.eth.get_transaction_count(address, "pending"),
                "chainId": web3.eth.chain_id,
            })

            signed_tx = web3.eth.account.sign_transaction(mint_tx, account)
            raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = web3.to_hex(raw_tx)
            receipt = await asyncio.to_thread(web3.eth.wait_for_transaction_receipt, tx_hash, timeout=300)
            block_number = receipt.blockNumber

            return tx_hash, block_number
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Claim PHRS Faucet {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None, None
            
    async def get_statistic(self, access_token: str, address: str, use_proxy: bool):
        proxy = self.get_next_proxy_for_account(address) if use_proxy else None
        connector = ProxyConnector.from_url(proxy) if proxy else None

        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {access_token}"
        
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(f"{self.BASE_API}/leaderboard/global?page=1&limit=10&referralCode={self.ref_code}", headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    return result
        except ClientResponseError as e:
            if e.status == 401:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Invalid Or Expired Access Token. {Style.RESET_ALL}"
                )
                self.access_tokens.pop(address, None)
            else:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Failed To Get Statistic {Style.RESET_ALL}"
                    f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                    f"{Fore.YELLOW+Style.BRIGHT} {e.status} {str(e)} {Style.RESET_ALL}                  "
                )
            return None
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}     Message :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed To Get Statistic {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}                  "
            )
            return None
        finally:
            if connector:
                await connector.close()
                
    async def process_account(self, account: str, use_proxy: bool):
        address = self.generate_address(account)
        if not address:
            return
        
        masked_account = self.mask_account(address)
        self.log(
            f"{Fore.GREEN+Style.BRIGHT}Account   :{Style.RESET_ALL}"
            f"{Fore.WHITE+Style.BRIGHT} {masked_account} {Style.RESET_ALL}"
        )

        try:
            signature = self.signatures.get(account)
            if not signature:
                signature = self.generate_signature(account)
                if not signature:
                    return
                self.signatures[account] = signature
            
            access_token = self.access_tokens.get(address)
            if not access_token:
                access_token = await self.get_access_token(account, address, signature, use_proxy)
                if not access_token:
                    return

            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT} Success Login {Style.RESET_ALL}"
            )
            
            user_info = await self.get_user_info(address, access_token, use_proxy)
            if user_info:
                daily_check_in = user_info["data"]["dailyCheckIn"]
                ref_count = user_info["data"]["refCount"]
                total_claim_phrs = user_info["data"]["totalClaimPhar"]
                
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Daily     :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {daily_check_in} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Referral  :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {ref_count} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}Total PHRS:{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {total_claim_phrs} {Style.RESET_ALL}"
                )

            # --- Check-In - Claim PHRS Faucet ---
            self.log(
                f"{Fore.YELLOW+Style.BRIGHT}Action    :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} Check-In {Style.RESET_ALL}"
            )
            check_in_result = await self.check_in(address, access_token, use_proxy)
            if check_in_result:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Status  :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}"
                )
            
            self.log(
                f"{Fore.YELLOW+Style.BRIGHT}Action    :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} Claim Faucet {Style.RESET_ALL}"
            )
            claim_faucet_result = await self.claim_faucet(address, access_token, use_proxy)
            if claim_faucet_result:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Status  :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}"
                )
            
            self.log(
                f"{Fore.YELLOW+Style.BRIGHT}Action    :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} Claim PHRS Faucet {Style.RESET_ALL}"
            )
            tx_hash, block_number = await self.claim_phrs_faucet(account, address, use_proxy)
            if tx_hash and block_number:
                explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Status  :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Block   :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Tx Hash :{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
                )
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}     Explorer:{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {explorer} {Style.RESET_ALL}"
                )
            
            if use_proxy:
                self.rotate_proxy_for_account(account)

        except Exception as e:
            self.log(
                f"{Fore.RED+Style.BRIGHT}Error Processing Account {masked_account}: {e}{Style.RESET_ALL}"
            )
        finally:
            self.log(
                f"{Fore.LIGHTBLACK_EX+Style.BRIGHT}───────────────────────────────────────────────────{Style.RESET_ALL}"
            )
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
    
    async def main(self):
        self.clear_terminal()
        self.welcome()

        # Load accounts first
        account_filename = "accounts.txt" # Changed from account.txt
        if not os.path.exists(account_filename):
            self.log(f"{Fore.RED + Style.BRIGHT}File {account_filename} Not Found. Please create it and add your private keys.{Style.RESET_ALL}")
            return

        with open(account_filename, "r") as f:
            accounts = [line.strip() for line in f.readlines()]
            if not accounts:
                self.log(f"{Fore.RED + Style.BRIGHT}No Accounts Found in {account_filename}. Please add private keys to the file.{Style.RESET_ALL}")
                return

        while True:
            self.clear_terminal()
            self.welcome()
            
            print(Fore.WHITE + Style.BRIGHT + "Select an option:")
            print(Fore.WHITE + Style.BRIGHT + "1. Check-In - Claim PHRS Faucet")
            print(Fore.WHITE + Style.BRIGHT + "2. Exit")
            
            option = int(input(Fore.YELLOW + Style.BRIGHT + ">> " + Style.RESET_ALL))

            if option == 1:
                print(Fore.WHITE + Style.BRIGHT + "Select proxy option:")
                print(Fore.WHITE + Style.BRIGHT + "1. Run with private proxy")
                print(Fore.WHITE + Style.BRIGHT + "2. Run without proxy")
                proxy_choice = int(input(Fore.YELLOW + Style.BRIGHT + ">> " + Style.RESET_ALL))

                use_proxy = False
                if proxy_choice == 1:
                    use_proxy = True
                    print(Fore.WHITE + Style.BRIGHT + "Choose proxy source:")
                    print(Fore.WHITE + Style.BRIGHT + "1. Scrape from proxyscrape.com")
                    print(Fore.WHITE + Style.BRIGHT + "2. Use proxy.txt")
                    proxy_source_choice = int(input(Fore.YELLOW + Style.BRIGHT + ">> " + Style.RESET_ALL))
                    await self.load_proxies(proxy_source_choice)
                elif proxy_choice == 2:
                    use_proxy = False
                else:
                    self.log(f"{Fore.RED + Style.BRIGHT}Invalid Proxy Option. Using without proxy.{Style.RESET_ALL}")
                    use_proxy = False

                self.min_delay = int(input(Fore.WHITE + Style.BRIGHT + "Enter min delay (seconds): " + Style.RESET_ALL))
                self.max_delay = int(input(Fore.WHITE + Style.BRIGHT + "Enter max delay (seconds): " + Style.RESET_ALL))
                
                tasks = [self.process_account(account, use_proxy) for account in accounts]
                await asyncio.gather(*tasks)

            elif option == 2:
                self.log(f"{Fore.YELLOW + Style.BRIGHT}Exiting program.{Style.RESET_ALL}")
                break
            else:
                self.log(f"{Fore.RED + Style.BRIGHT}Invalid Option. Please Try Again.{Style.RESET_ALL}")
            
            self.log(
                f"{Fore.WHITE+Style.BRIGHT}Done All Accounts...{Style.RESET_ALL}"
            )
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(PharosTestnet().main())
