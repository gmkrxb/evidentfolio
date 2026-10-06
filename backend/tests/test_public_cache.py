from types import SimpleNamespace

from app.api.routes.public import public_cache_control


def request(query: dict) -> SimpleNamespace:
    return SimpleNamespace(query_params=query)


def test_fingerprinted_public_asset_is_immutable():
    asset = SimpleNamespace(is_public=True, sha256="ecb5ed41c19bfbd2" + "0" * 48)
    assert public_cache_control(request({"v": "ecb5ed41c19bfbd2"}), asset) == "public, max-age=31536000, immutable"


def test_stale_or_missing_fingerprint_revalidates():
    asset = SimpleNamespace(is_public=True, sha256="ecb5ed41c19bfbd2" + "0" * 48)
    assert public_cache_control(request({"v": "0000000000000000"}), asset) == "public, no-cache"
    assert public_cache_control(request({}), asset) == "public, no-cache"


def test_private_asset_is_never_cached():
    asset = SimpleNamespace(is_public=False, sha256="ecb5ed41c19bfbd2" + "0" * 48)
    assert public_cache_control(request({"v": "ecb5ed41c19bfbd2"}), asset) == "private, no-store"
