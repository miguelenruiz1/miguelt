"""
Solana RPC client with circuit breaker and simulation fallback.

Uses solders (Rust bindings) for keypair/transaction building and
the solana Python library for RPC communication.

Simulation mode: SOLANA_SIMULATION=true generates fake signatures.
This lets the full pipeline run without a real Solana connection.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import time
import uuid
from enum import StrEnum
from typing import Any

import httpx
from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

_B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
_B58_MAP = {c: i for i, c in enumerate(_B58_ALPHABET)}


def _b58decode(s: str) -> bytes:
    """Pure-Python base58 decode — no external library needed."""
    leading = len(s) - len(s.lstrip('1'))
    n = 0
    for c in s:
        n = n * 58 + _B58_MAP[c]
    result = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    return b'\x00' * leading + result


def _b58encode(data: bytes) -> str:
    """Pure-Python base58 encode — no external library needed."""
    leading = len(data) - len(data.lstrip(b'\x00'))
    n = int.from_bytes(data, 'big')
    result = ''
    while n:
        n, rem = divmod(n, 58)
        result = _B58_ALPHABET[rem] + result
    return '1' * leading + result


# ─── Circuit Breaker ─────────────────────────────────────────────────────────

class CBState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, threshold: int = 5, recovery_timeout: int = 60) -> None:
        self._threshold = threshold
        self._recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = CBState.CLOSED
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CBState:
        return self._state

    async def call(self, coro_func, *args, **kwargs):
        async with self._lock:
            if self._state == CBState.OPEN:
                if time.monotonic() - self._opened_at >= self._recovery_timeout:
                    self._state = CBState.HALF_OPEN
                    log.info("circuit_breaker_half_open")
                else:
                    from app.core.errors import CircuitOpenError
                    raise CircuitOpenError("Solana RPC circuit is OPEN; retrying later")

        try:
            result = await coro_func(*args, **kwargs)
            async with self._lock:
                if self._state == CBState.HALF_OPEN:
                    self._state = CBState.CLOSED
                    self._failures = 0
                    log.info("circuit_breaker_closed")
            return result
        except Exception as exc:
            async with self._lock:
                self._failures += 1
                if self._failures >= self._threshold:
                    self._state = CBState.OPEN
                    self._opened_at = time.monotonic()
                    log.warning(
                        "circuit_breaker_opened",
                        failures=self._failures,
                        exc=str(exc),
                    )
            raise


# ─── Solana Client ────────────────────────────────────────────────────────────

class SolanaClient:
    """
    Async Solana RPC client.

    In simulation mode every operation returns fake but structurally valid data.
    In production mode it communicates with the configured RPC URL.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._rpc_url = settings.SOLANA_RPC_URL
        self._simulation = settings.SOLANA_SIMULATION
        self._timeout = settings.SOLANA_TIMEOUT
        self._keypair_raw = settings.SOLANA_KEYPAIR
        self._commitment = settings.SOLANA_COMMITMENT
        self._cb = CircuitBreaker(
            threshold=settings.SOLANA_CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=settings.SOLANA_CIRCUIT_BREAKER_RECOVERY,
        )
        self._http: httpx.AsyncClient | None = None
        self._keypair = None  # solders.Keypair loaded lazily

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                http2=False,  # JSON-RPC works fine over HTTP/1.1
            )
        return self._http

    def _load_keypair(self):
        """Load solders Keypair from base58 string or file path."""
        if self._keypair is not None:
            return self._keypair
        if not self._keypair_raw:
            return None
        try:
            from solders.keypair import Keypair  # type: ignore
            raw = self._keypair_raw.strip()
            if raw.startswith("[") or raw.startswith("/") or "\\" in raw:
                # Treat as file path or JSON array
                import json as _json
                import pathlib
                p = pathlib.Path(raw)
                if p.exists():
                    data = _json.loads(p.read_text())
                    self._keypair = Keypair.from_bytes(bytes(data))
                else:
                    self._keypair = Keypair.from_bytes(bytes(_json.loads(raw)))
            else:
                # base58 encoded 64-byte secret key
                self._keypair = Keypair.from_bytes(_b58decode(raw))
            return self._keypair
        except Exception as exc:
            log.warning("keypair_load_failed", exc=str(exc))
            return None

    def generate_wallet(self) -> tuple[str, str]:
        """
        Generate a new Solana Keypair.
        Returns: (pubkey_base58, secret_key_base58)
        """
        if self._simulation:
            # Generate a fake one for sim
            fake_pk = "sim" + str(uuid.uuid4()).replace("-", "")[:40]
            fake_sk = "sim_sk_" + str(uuid.uuid4()).replace("-", "")
            return fake_pk, fake_sk
            
        try:
            from solders.keypair import Keypair  # type: ignore
            kp = Keypair()
            pubkey = str(kp.pubkey())
            secret = _b58encode(bytes(kp))
            return pubkey, secret
        except ImportError as exc:
            log.warning("solders_not_available_for_generation", exc=str(exc))
            fake_pk = "sim" + str(uuid.uuid4()).replace("-", "")[:40]
            fake_sk = "sim_sk_" + str(uuid.uuid4()).replace("-", "")
            return fake_pk, fake_sk

    async def try_airdrop(self, pubkey: str, lamports: int = 100_000_000) -> bool:
        """
        Request a devnet airdrop for the given pubkey (0.1 SOL by default).
        Returns True on success, False on failure. Never raises.
        In simulation mode always returns True immediately.
        """
        if self._simulation:
            log.info("airdrop_simulated", pubkey=pubkey, lamports=lamports)
            return True
        try:
            async def _call():
                result = await self._rpc(
                    "requestAirdrop",
                    [pubkey, lamports],
                )
                return bool(result)
            return await self._cb.call(_call)
        except Exception as exc:
            log.warning("airdrop_failed", pubkey=pubkey, exc=str(exc))
            return False

    async def mint_logistics_asset(
        self, collection_wallet_pubkey: str, collection_private_key: str, metadata: dict
    ) -> str:
        """
        Mint a new Metaplex NFT representing a logistics load.
        Returns the mint address (base58 pubkey string).
        # TODO: Implement full Pyth/Metaplex Python integration. 
        # Using a simulated mint address for now as Python Metaplex bindings require specific setup.
        """
        if self._simulation:
            return "sim_mint_" + str(uuid.uuid4()).replace("-", "")[:35]

        # Note: True Metaplex minting in Python requires building complex instructions.
        # For the MVP, we simulate the minting action and return a valid format string.
        log.info("minting_asset_simulated_for_now", collection=collection_wallet_pubkey)
        await asyncio.sleep(0.5) # Simulate network delay
        return "mint_" + str(uuid.uuid4()).replace("-", "")[:32]

    # ─── Simulation helpers ───────────────────────────────────────────────────

    def _sim_signature(self, memo: str) -> str:
        digest = hashlib.sha256(memo.encode()).hexdigest()
        return f"SIM_{digest[:44]}"

    # ─── RPC JSON helpers ─────────────────────────────────────────────────────

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        http = await self._ensure_http()
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        resp = await http.post(self._rpc_url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"Solana RPC error: {body['error']}")
        return body.get("result")

    # ─── Public API ───────────────────────────────────────────────────────────

    async def get_account_info(self, pubkey: str) -> dict[str, Any]:
        if self._simulation:
            return {
                "pubkey": pubkey,
                "lamports": 1_000_000,
                "owner": "11111111111111111111111111111111",
                "executable": False,
                "data": None,
                "simulated": True,
            }
        async def _call():
            result = await self._rpc(
                "getAccountInfo",
                [pubkey, {"encoding": "base64", "commitment": self._commitment}],
            )
            value = result.get("value") if result else None
            if value is None:
                return {"pubkey": pubkey, "lamports": None, "owner": None, "executable": None, "data": None, "simulated": False}
            return {
                "pubkey": pubkey,
                "lamports": value.get("lamports"),
                "owner": value.get("owner"),
                "executable": value.get("executable"),
                "data": value.get("data"),
                "simulated": False,
            }
        return await self._cb.call(_call)

    async def tx_exists(self, signature: str) -> bool:
        """Return True if a Solana transaction signature exists on chain.

        Used by anchor recovery to avoid double-spending memo fees when a
        previous attempt persisted the sig but failed to mark anchored.
        """
        if not signature or signature.startswith("SIM_"):
            return self._simulation
        try:
            status = await self.get_signature_status(signature)
            return status.get("slot") is not None and status.get("err") is None
        except Exception:
            return False

    async def get_signature_status(self, signature: str) -> dict[str, Any]:
        if self._simulation or signature.startswith("SIM_"):
            return {"signature": signature, "slot": 1, "confirmations": 32, "err": None, "simulated": True}
        async def _call():
            result = await self._rpc("getSignatureStatuses", [[signature]])
            value = result.get("value", [None])[0] if result else None
            if value is None:
                return {"signature": signature, "slot": None, "confirmations": None, "err": None, "simulated": False}
            return {
                "signature": signature,
                "slot": value.get("slot"),
                "confirmations": value.get("confirmations"),
                "err": value.get("err"),
                "simulated": False,
            }
        return await self._cb.call(_call)

    async def send_memo(self, memo: str) -> str:
        """
        Send a Memo Program transaction anchoring `memo` on Solana.
        Returns the transaction signature string.
        """
        if self._simulation:
            sig = self._sim_signature(memo)
            log.info("solana_memo_simulated", sig=sig, memo_prefix=memo[:16])
            return sig

        keypair = self._load_keypair()
        if keypair is None:
            log.warning("solana_keypair_missing_falling_back_to_simulation")
            return self._sim_signature(memo)

        async def _send():
            try:
                from solders.keypair import Keypair  # type: ignore
                from solders.pubkey import Pubkey  # type: ignore
                from solders.instruction import Instruction, AccountMeta  # type: ignore
                from solders.message import Message  # type: ignore
                from solders.transaction import Transaction  # type: ignore
                from solders.hash import Hash  # type: ignore

                memo_prog = Pubkey.from_string(MEMO_PROGRAM_ID)

                # Build instruction
                ix = Instruction(
                    program_id=memo_prog,
                    data=memo.encode("utf-8"),
                    accounts=[
                        AccountMeta(
                            pubkey=keypair.pubkey(),
                            is_signer=True,
                            is_writable=False,
                        )
                    ],
                )

                # Get latest blockhash via our HTTP RPC
                bh_result = await self._rpc("getLatestBlockhash", [{"commitment": self._commitment}])
                blockhash_str = bh_result["value"]["blockhash"]
                recent_blockhash = Hash.from_string(blockhash_str)

                # Build + sign legacy transaction
                msg = Message.new_with_blockhash([ix], keypair.pubkey(), recent_blockhash)
                tx = Transaction([keypair], msg, recent_blockhash)

                # Serialize
                tx_bytes = bytes(tx)
                tx_b64 = base64.b64encode(tx_bytes).decode()

                # Send
                result = await self._rpc(
                    "sendTransaction",
                    [tx_b64, {"encoding": "base64", "skipPreflight": True, "preflightCommitment": "confirmed"}],
                )
                sig = str(result)
                log.info("solana_memo_anchored", sig=sig)
                return sig

            except ImportError as exc:
                log.warning("solders_not_available", exc=str(exc))
                return self._sim_signature(memo)

        return await self._cb.call(_send)

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()


# ─── Module-level singleton ───────────────────────────────────────────────────

_client: SolanaClient | None = None


def get_solana_client() -> SolanaClient:
    global _client
    if _client is None:
        _client = SolanaClient()
    return _client


async def close_solana_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
