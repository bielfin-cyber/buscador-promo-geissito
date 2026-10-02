import unittest

from core import _fingerprint, _safe_source_link, _to_offer, normalize


class CoreTests(unittest.TestCase):
    def test_normalize_accents(self):
        self.assertEqual(normalize("Tênis Masculino"), "tenis masculino")

    def test_reject_relative_or_unsafe_links(self):
        for value in ["/produto/1", "javascript:alert(1)", "", "https://x.test/a\nB"]:
            with self.assertRaises(ValueError):
                _safe_source_link(value)

    def test_exact_link_is_preserved(self):
        url = "https://s.shopee.com.br/AbCd?lp=aff&utm_source=x"
        offer = _to_offer(
            {
                "id": "1",
                "title": "Tênis masculino",
                "price": "99.90",
                "old_price": "199.80",
                "link": url,
                "stores": [{"store": {"name": "Shopee"}}],
            }
        )
        self.assertEqual(offer.affiliate_url, url)
        self.assertEqual(offer.link_fingerprint, _fingerprint(url))
        self.assertEqual(offer.discount, 50)


if __name__ == "__main__":
    unittest.main()

