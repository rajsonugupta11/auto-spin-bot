import aiohttp
import asyncio
import brotli
import gzip
import random
import re
from colorama import init as colorama_init, Fore, Style
from keep_alive import keep_alive

colorama_init(autoreset=True)

# 🔹 Replace this with your own GitHub raw link
TOKENS_URL = "https://raw.githubusercontent.com/rajsonugupta11/auto-spin-bot/main/tokens.txt"
BALANCE_URL = "https://zero-api.kaisar.io/user/balances?symbol=point"
SPIN_URL = "https://zero-api.kaisar.io/lucky/spin"
CONVERT_URL = "https://zero-api.kaisar.io/lucky/convert"

timeout = aiohttp.ClientTimeout(total=10)

ACCOUNT_COLORS = [
    Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE,
    Fore.MAGENTA, Fore.CYAN, Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX,
    Fore.LIGHTYELLOW_EX, Fore.LIGHTBLUE_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX
]

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/134.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) Chrome/115.0.5790.171 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) Chrome/115.0.5790.171 Mobile Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) Chrome/115.0.5790.171 Mobile Safari/537.36"
]

def get_headers(token):
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "authorization": f"Bearer {token.strip()}",
        "content-type": "application/json",
        "origin": "https://zero.kaisar.io",
        "referer": "https://zero.kaisar.io/",
        "user-agent": random.choice(USER_AGENTS),
    }

async def decode_response(resp):
    raw_data = await resp.read()
    encoding = resp.headers.get("content-encoding", "")
    try:
        if "br" in encoding:
            raw_data = brotli.decompress(raw_data)
        elif "gzip" in encoding:
            raw_data = gzip.decompress(raw_data)
    except:
        pass
    return raw_data.decode("utf-8", errors="ignore")

async def is_token_valid(session, headers):
    try:
        async with session.get(BALANCE_URL, headers=headers) as resp:
            return resp.status == 200
    except:
        return False

async def check_balance(session, headers, name, color):
    try:
        async with session.get(BALANCE_URL, headers=headers) as resp:
            decoded = await decode_response(resp)
            match = re.search(r'"balance":"?([\d.]+)"?', decoded)
            if match:
                balance = float(match.group(1))
                print(f"{color}[{name}] 💰 Balance: {Fore.YELLOW}{balance}")
                return balance
    except:
        pass
    return None

async def buy_ticket(session, headers, count, name, color):
    try:
        if count <= 0:
            return
        await session.post(CONVERT_URL, headers=headers, json={})
        print(f"{color}[{name}] 🎟 Ticket purchased: {count}")
    except Exception as e:
        print(f"{color}[{name}] Ticket error: {e}")

async def spin(session, headers, sem):
    async with sem:
        try:
            headers["user-agent"] = random.choice(USER_AGENTS)
            async with session.post(SPIN_URL, headers=headers, json={}) as resp:
                return resp.status
        except:
            return None

async def worker(token, target, name, color):
    headers = get_headers(token)
    sem = asyncio.Semaphore(100)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if not await is_token_valid(session, headers):
            print(f"{color}[{name}] ❌ Invalid token")
            return

        while True:
            balance = await check_balance(session, headers, name, color)
            if balance is None:
                await asyncio.sleep(5)
                continue

            if balance >= target:
                print(f"{color}[{name}] 🎯 Target {target} reached!")
                break

            if balance >= 300:
                await buy_ticket(session, headers, 1, name, color)
            else:
                await asyncio.sleep(50)
                continue

            tasks = [spin(session, headers, sem) for _ in range(300)]
            results = await asyncio.gather(*tasks)
            hits = sum(1 for r in results if r == 200)
            print(f"{color}[{name}] 🎰 Spins: {hits}")
            await asyncio.sleep(1)

async def fetch_tokens():
    async with aiohttp.ClientSession() as session:
        async with session.get(TOKENS_URL) as resp:
            data = await resp.text()
            return [t.strip() for t in data.splitlines() if t.strip()]

async def run_cycle():
    tokens = await fetch_tokens()
    target = 100000
    tasks = []
    for i, token in enumerate(tokens):
        color = ACCOUNT_COLORS[i % len(ACCOUNT_COLORS)]
        tasks.append(worker(token, target, f"Account #{i+1}", color))
    await asyncio.gather(*tasks)

async def main():
    keep_alive()
    while True:
        print(f"{Fore.CYAN}🚀 New 24-hour cycle started")
        await run_cycle()
        print(f"{Fore.MAGENTA}Sleeping 24 hours before next refresh...")
        await asyncio.sleep(24 * 3600)

asyncio.run(main())
