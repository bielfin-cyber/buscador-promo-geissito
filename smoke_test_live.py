from core import OfferIndex


def main():
    index = OfferIndex(ttl_seconds=900)
    for query in ("air fryer", "TV 50", "tênis masculino"):
        offers, stats = index.search(query, limit=5)
        print(f"\n{query!r}: {len(offers)} resultado(s); {stats.get('accepted')} indexadas")
        for offer in offers:
            assert offer.affiliate_url
            print(f"- {offer.title} | {offer.store} | {offer.price} | {offer.affiliate_url}")


if __name__ == "__main__":
    main()

