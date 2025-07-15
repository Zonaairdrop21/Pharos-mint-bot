import os
import time
import secrets
import string
import random
import sys
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = "https://testnet.dplabs-internal.com"
CONTRACT_ADDRESS = "0x51Be1Ef20A1fD5179419738fC71D95a8B6F8A175"
ACCOUNTS_FILE = "accounts.txt"

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
        }
    ]
)

if not w3.is_connected():
    print("❌ Gagal konek RPC")
    sys.exit(1)
else:
    print("✅ Terkoneksi ke Pharos RPC")

def load_wallets():
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        return [{
            'private_key': '0x' + l if not l.startswith('0x') else l,
            'address': w3.eth.account.from_key(l).address
        } for l in lines]
    except Exception as e:
        print(f"❌ Gagal load akun: {e}")
        return []

def random_domain(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def get_gas_price():
    try:
        return w3.eth.gas_price
    except:
        return Web3.to_wei(1, 'gwei')

def sign_and_send(tx, pk):
    try:
        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        print(f"✅ TX berhasil: {tx_hash.hex()}")
        return receipt.status == 1
    except Exception as e:
        print(f"❌ TX error: {e}")
        return False

def mint_domain(wallet):
    addr = wallet['address']
    pk = wallet['private_key']

    while True:
        domain = random_domain()
        print(f"\n🚀 Coba mint domain: {domain}.phrs untuk {addr}")
        secret = secrets.token_bytes(32)
        gas = get_gas_price()
        nonce = w3.eth.get_transaction_count(addr)

        try:
            commitment = contract.functions.makeCommitment(domain, addr, secret).call()
            tx = contract.functions.commit(commitment).build_transaction({
                'from': addr,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': gas
            })
            if sign_and_send(tx, pk):
                print(f"⏳ Menunggu 60 detik sebelum register...")
                time.sleep(60)

                nonce = w3.eth.get_transaction_count(addr)
                fee = Web3.to_wei(0.001, 'ether')
                register_tx = contract.functions.register(domain, addr, secret, 31536000).build_transaction({
                    'from': addr,
                    'nonce': nonce,
                    'gas': 300000,
                    'gasPrice': gas,
                    'value': fee
                })

                if sign_and_send(register_tx, pk):
                    print(f"🎉 Berhasil mint: {domain}.phrs")
                else:
                    print("❌ Gagal saat register.")
                break
            else:
                print("❌ Gagal commit, lanjut ke domain berikutnya...")
        except Exception as e:
            print(f"❌ Error saat proses: {e}")
        print("🕐 Delay 5 detik ke domain berikutnya...")
        time.sleep(5)

if __name__ == '__main__':
    wallets = load_wallets()
    print(f"🔑 Loaded {len(wallets)} wallet")
    for wallet in wallets:
        mint_domain(wallet)
