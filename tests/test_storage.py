import pytest
from bsc_watcher.storage import Storage


@pytest.fixture
def store(tmp_path):
    db_file = tmp_path / "test_watcher.db"
    s = Storage(str(db_file))
    yield s
    s.close()


def test_checkpoint_block(store):
    assert store.get_last_block() == 0
    store.set_last_block(123456)
    assert store.get_last_block() == 123456
    store.set_last_block(123500)
    assert store.get_last_block() == 123500


def test_save_pair_dedup(store):
    res1 = store.save_pair(
        pair_address="0xpair1",
        token0="0xt0",
        token1="0xt1",
        block_number=100,
        tx_hash="0xtx1",
    )
    assert res1 is True

    res2 = store.save_pair(
        pair_address="0xpair1",
        token0="0xt0",
        token1="0xt1",
        block_number=101,
        tx_hash="0xtx2",
    )
    assert res2 is False

    pairs = store.get_recent_pairs(limit=10)
    assert len(pairs) == 1
    assert pairs[0]["pair_address"] == "0xpair1"


def test_record_mint_idempotency(store):
    tx = "0xminttx1"
    pair = "0xpair1"
    assert not store.has_mint(tx, pair)

    store.record_mint(tx, pair, 1000, 2000, 105)
    assert store.has_mint(tx, pair)

    # Second insert shouldn't throw primary key or uniqueness error
    store.record_mint(tx, pair, 1000, 2000, 105)
    assert store.has_mint(tx, pair)
