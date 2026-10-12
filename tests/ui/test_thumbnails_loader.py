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

    t = thumbs.load_async(
        [Path("/tmp/a.pdf")], lambda p, b: ready.append((p, b)), is_current=lambda: True
    )
    t.join(timeout=5)
    t = thumbs.load_async(
        [Path("/tmp/a.pdf")], lambda p, b: ready.append((p, b)), is_current=lambda: True
    )
    t.join(timeout=5)

    assert len(rendered) == 1  # segunda vez sale de caché
    assert len(ready) == 2  # pero on_ready se notifica igual
    assert ready[0] == (Path("/tmp/a.pdf"), b"png-falso")
    assert thumbs.get_cached(Path("/tmp/a.pdf")) == b"png-falso"


def test_none_result_is_cached_and_not_retried(monkeypatch):
    rendered = []

    def fake_none(path, page_index=0, height_px=56):
        rendered.append(path)
        return None

    monkeypatch.setattr(thumbs, "render_thumbnail", fake_none)
    for _ in range(2):
        t = thumbs.load_async(
            [Path("/tmp/p.pdf")], lambda p, b: None, is_current=lambda: True
        )
        t.join(timeout=5)

    assert len(rendered) == 1
    assert thumbs.get_cached(Path("/tmp/p.pdf")) is None  # None cacheado ≠ MISSING


def test_missing_sentinel_for_never_tried():
    assert thumbs.get_cached(Path("/tmp/nunca.pdf")) is thumbs.MISSING


def test_lru_evicts_oldest(monkeypatch):
    monkeypatch.setattr(thumbs, "_CACHE_MAX", 2)
    thumbs._store(thumbs._key(Path("a")), b"1")
    thumbs._store(thumbs._key(Path("b")), b"2")
    thumbs._store(thumbs._key(Path("c")), b"3")  # expulsa "a"

    assert thumbs.get_cached(Path("a")) is thumbs.MISSING
    assert thumbs.get_cached(Path("b")) == b"2"
    assert thumbs.get_cached(Path("c")) == b"3"


def test_stale_generation_never_notifies(monkeypatch):
    monkeypatch.setattr(thumbs, "render_thumbnail", _fake_render([]))
    ready = []

    t = thumbs.load_async(
        [Path("/tmp/a.pdf")], lambda p, b: ready.append(p), is_current=lambda: False
    )
    t.join(timeout=5)

    assert ready == []


def test_cache_is_invalidated_when_the_file_changes(tmp_path, monkeypatch):
    rendered = []
    monkeypatch.setattr(thumbs, "render_thumbnail", _fake_render(rendered))
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"version 1")
    thumbs.load_async([pdf], lambda p, b: None, is_current=lambda: True).join(5)
    assert thumbs.get_cached(pdf) == b"png-falso"

    pdf.write_bytes(b"version 2, mas larga")

    assert thumbs.get_cached(pdf) is thumbs.MISSING
    thumbs.load_async([pdf], lambda p, b: None, is_current=lambda: True).join(5)
    assert len(rendered) == 2


def test_any_page_can_be_requested(monkeypatch):
    calls = []

    def fake(path, page_index=0, height_px=56):
        calls.append(page_index)
        return b"p%d" % page_index

    monkeypatch.setattr(thumbs, "render_thumbnail", fake)
    ready = []
    doc = Path("/tmp/doc.pdf")
    thumbs.load_async(
        [(doc, 0), (doc, 3)], lambda item, b: ready.append((item, b)), lambda: True
    ).join(5)

    assert sorted(calls) == [0, 3]
    assert sorted(ready) == [((doc, 0), b"p0"), ((doc, 3), b"p3")]
    assert thumbs.get_cached(doc, 3) == b"p3"


def test_rendering_uses_every_worker(monkeypatch):
    import threading
    import time

    threads = set()

    def slow(path, page_index=0, height_px=56):
        threads.add(threading.current_thread().name)
        time.sleep(0.05)
        return b"x"

    monkeypatch.setattr(thumbs, "render_thumbnail", slow)
    paths = [Path(f"/tmp/{i}.pdf") for i in range(8)]
    thumbs.load_async(paths, lambda p, b: None, lambda: True).join(5)

    assert len(threads) == thumbs._MAX_WORKERS


def test_ui_flushes_are_batched(monkeypatch):
    monkeypatch.setattr(thumbs, "render_thumbnail", _fake_render([]))
    events = []
    paths = [Path(f"/tmp/{i}.pdf") for i in range(40)]

    thumbs.load_async(
        paths,
        lambda p, b: events.append("ready"),
        lambda: True,
        on_flush=lambda: events.append("flush"),
    ).join(5)

    assert events.count("ready") == 40
    assert 1 <= events.count("flush") < 40
    assert events[-1] == "flush"
