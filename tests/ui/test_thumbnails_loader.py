from pathlib import Path

import pytest

import pdftool.ui.thumbnails as thumbs


@pytest.fixture(autouse=True)
def _clean_cache():
    thumbs._cache.clear()
    yield
    thumbs._cache.clear()


def _fake_render(counter):
    def fake(path, page_index=0, height_px=56):
        counter.append(path)
        return b"png-falso"
    return fake


def test_cache_avoids_second_render(monkeypatch):
    rendered = []
    monkeypatch.setattr(thumbs, "render_thumbnail", _fake_render(rendered))
    ready = []

    t = thumbs.load_async([Path("/tmp/a.pdf")], lambda p, b: ready.append((p, b)),
                          is_current=lambda: True)
    t.join(timeout=5)
    t = thumbs.load_async([Path("/tmp/a.pdf")], lambda p, b: ready.append((p, b)),
                          is_current=lambda: True)
    t.join(timeout=5)

    assert len(rendered) == 1          # segunda vez sale de caché
    assert len(ready) == 2             # pero on_ready se notifica igual
    assert ready[0] == (Path("/tmp/a.pdf"), b"png-falso")
    assert thumbs.get_cached(Path("/tmp/a.pdf")) == b"png-falso"


def test_none_result_is_cached_and_not_retried(monkeypatch):
    rendered = []

    def fake_none(path, page_index=0, height_px=56):
        rendered.append(path)
        return None

    monkeypatch.setattr(thumbs, "render_thumbnail", fake_none)
    for _ in range(2):
        t = thumbs.load_async([Path("/tmp/p.pdf")], lambda p, b: None,
                              is_current=lambda: True)
        t.join(timeout=5)

    assert len(rendered) == 1
    assert thumbs.get_cached(Path("/tmp/p.pdf")) is None  # None cacheado ≠ MISSING


def test_missing_sentinel_for_never_tried():
    assert thumbs.get_cached(Path("/tmp/nunca.pdf")) is thumbs.MISSING


def test_lru_evicts_oldest(monkeypatch):
    monkeypatch.setattr(thumbs, "_CACHE_MAX", 2)
    thumbs._store(("a", 0, 56), b"1")
    thumbs._store(("b", 0, 56), b"2")
    thumbs._store(("c", 0, 56), b"3")  # expulsa "a"

    assert thumbs.get_cached(Path("a")) is thumbs.MISSING
    assert thumbs.get_cached(Path("b")) == b"2"
    assert thumbs.get_cached(Path("c")) == b"3"


def test_stale_generation_never_notifies(monkeypatch):
    monkeypatch.setattr(thumbs, "render_thumbnail", _fake_render([]))
    ready = []

    t = thumbs.load_async([Path("/tmp/a.pdf")], lambda p, b: ready.append(p),
                          is_current=lambda: False)
    t.join(timeout=5)

    assert ready == []
