from __future__ import annotations

import hashlib
import math
import re
import threading
import time
import unicodedata
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


SITE_URL = "https://www.afiliadointeligente.com.br/promo-do-geissito"
TRPC_URL = (
    "https://www.afiliadointeligente.com.br/api/trpc/"
    "site.getProductsBySlugPaginated"
)
SLUG = "promo-do-geissito"
PAGE_SIZE = 120


class SourceError(RuntimeError):
    """Raised when the source cannot provide a safe, usable catalogue."""


@dataclass(frozen=True)
class Offer:
    id: str
    title: str
    store: str
    price: Decimal | None
    old_price: Decimal | None
    discount: int | None
    affiliate_url: str
    image: str | None
    coupon: str | None
    created_at: str | None
    tags: tuple[str, ...]
    link_fingerprint: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _money(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number > 0 else None


def _safe_source_link(value: Any) -> str:
    """Accept only the exact absolute HTTP(S) URL returned in product.link."""
    url = _text(value)
    if not url or any(ch in url for ch in "\r\n\t"):
        raise ValueError("link ausente ou malformado")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("link não é uma URL HTTP(S) absoluta")
    if parsed.username or parsed.password:
        raise ValueError("link contém credenciais")
    return url


def _fingerprint(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _extract_store(raw: dict[str, Any]) -> str:
    for relation in raw.get("stores") or []:
        store = relation.get("store") or {}
        name = _text(store.get("name"))
        if name:
            return name
    return "Loja não informada"


def _to_offer(raw: dict[str, Any]) -> Offer:
    affiliate_url = _safe_source_link(raw.get("link"))
    title = _text(raw.get("title"))
    if not title:
        raise ValueError("produto sem título")
    price = _money(raw.get("price"))
    old_price = _money(raw.get("old_price"))
    discount = None
    if price is not None and old_price is not None and old_price > price:
        discount = round(float((old_price - price) / old_price * 100))
    tags = tuple(
        name
        for item in raw.get("tags") or []
        if (name := _text((item.get("tag") or {}).get("name")))
    )
    image = _text(raw.get("image")) or None
    coupon = _text(raw.get("coupon")) or None
    return Offer(
        id=_text(raw.get("id")) or _fingerprint(affiliate_url)[:16],
        title=title,
        store=_extract_store(raw),
        price=price,
        old_price=old_price,
        discount=discount,
        affiliate_url=affiliate_url,
        image=image,
        coupon=coupon,
        created_at=_text(raw.get("created_at")) or None,
        tags=tags,
        link_fingerprint=_fingerprint(affiliate_url),
    )


class AffiliateInteligenteClient:
    def __init__(self, timeout: int = 30, page_size: int = PAGE_SIZE) -> None:
        self.timeout = timeout
        self.page_size = page_size
        self.headers = {
            "User-Agent": "PromoDoGeissitoBuscador/1.0 (+uso-pessoal)",
            "Accept": "application/json",
            "Referer": SITE_URL,
        }

    def fetch_page(self, page_index: int) -> dict[str, Any]:
        payload = {
            "0": {
                "json": {
                    "slug": SLUG,
                    "pageIndex": page_index,
                    "limit": self.page_size,
                }
            }
        }
        try:
            query = urlencode({"batch": "1", "input": json.dumps(payload)})
            request = Request(f"{TRPC_URL}?{query}", headers=self.headers)
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body[0]["result"]["data"]["json"]
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise SourceError(f"Falha ao consultar a fonte: {exc}") from exc

    def fetch_all(self, max_pages: int | None = None) -> tuple[list[Offer], dict[str, int]]:
        first_page = self.fetch_page(0)
        total_reported = int(first_page.get("totalProducts") or 0)
        total_pages = max(1, math.ceil(total_reported / self.page_size))
        if max_pages is not None:
            total_pages = min(total_pages, max_pages)
        pages: dict[int, dict[str, Any]] = {0: first_page}
        if total_pages > 1:
            with ThreadPoolExecutor(max_workers=min(8, total_pages - 1)) as executor:
                futures = {executor.submit(self.fetch_page, page): page for page in range(1, total_pages)}
                for future in as_completed(futures):
                    pages[futures[future]] = future.result()

        offers: list[Offer] = []
        rejected = 0
        seen_ids: set[str] = set()
        seen_links: set[str] = set()
        for page in range(total_pages):
            data = pages[page]
            for raw in data.get("products") or []:
                try:
                    offer = _to_offer(raw)
                except (ValueError, TypeError):
                    rejected += 1
                    continue
                # Deduplicate without ever rewriting the source affiliate URL.
                if offer.id in seen_ids or offer.link_fingerprint in seen_links:
                    continue
                seen_ids.add(offer.id)
                seen_links.add(offer.link_fingerprint)
                offers.append(offer)
        return offers, {
            "source_total": total_reported,
            "accepted": len(offers),
            "rejected": rejected,
            "pages": total_pages,
        }


class OfferIndex:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._loaded_at = 0.0
        self._offers: list[Offer] = []
        self._stats: dict[str, int] = {}

    def refresh(self, force: bool = False) -> tuple[list[Offer], dict[str, int]]:
        with self._lock:
            fresh = self._offers and time.time() - self._loaded_at < self.ttl_seconds
            if fresh and not force:
                return self._offers, self._stats
            offers, stats = AffiliateInteligenteClient().fetch_all()
            if not offers:
                raise SourceError("A fonte respondeu, mas nenhuma oferta segura foi encontrada.")
            self._offers, self._stats, self._loaded_at = offers, stats, time.time()
            return self._offers, self._stats

    def search(self, query: str, limit: int = 24) -> tuple[list[Offer], dict[str, int]]:
        query_normalized = normalize(query)
        tokens = query_normalized.split()
        if not tokens:
            return [], self._stats
        offers, stats = self.refresh()

        def score(offer: Offer) -> tuple[float, str]:
            title = normalize(offer.title)
            tags = normalize(" ".join(offer.tags))
            store = normalize(offer.store)
            haystack = f"{title} {tags} {store}"
            if not all(token in haystack for token in tokens):
                return (-1.0, offer.title)
            value = 100.0 if query_normalized in title else 0.0
            value += sum(20 for token in tokens if token in title)
            value += sum(5 for token in tokens if token in tags)
            value += offer.discount or 0
            return (value, offer.title)

        ranked = [(score(offer), offer) for offer in offers]
        ranked = [item for item in ranked if item[0][0] >= 0]
        ranked.sort(key=lambda item: (-item[0][0], normalize(item[0][1])))
        return [offer for _, offer in ranked[:limit]], stats


def brl(value: Decimal | None) -> str:
    if value is None:
        return "Preço não informado"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"

