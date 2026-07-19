from pathlib import Path

import pdftool.ui.platform as platform


def test_open_folder_darwin(monkeypatch):
    calls = {}
    monkeypatch.setattr(platform.sys, "platform", "darwin")
    monkeypatch.setattr(platform.subprocess, "run",
                        lambda *a, **k: calls.setdefault("args", a))
    platform.open_folder(Path("/tmp/x"))
    assert calls["args"][0] == ["open", "/tmp/x"]


def test_open_folder_linux(monkeypatch):
    calls = {}
    monkeypatch.setattr(platform.sys, "platform", "linux")
    monkeypatch.setattr(platform.subprocess, "run",
                        lambda *a, **k: calls.setdefault("args", a))
    platform.open_folder(Path("/tmp/x"))
    assert calls["args"][0] == ["xdg-open", "/tmp/x"]


def test_open_file_darwin(monkeypatch):
    calls = {}
    monkeypatch.setattr(platform.sys, "platform", "darwin")
    monkeypatch.setattr(platform.subprocess, "run",
                        lambda *a, **k: calls.setdefault("args", a))
    platform.open_file(Path("/tmp/x.pdf"))
    assert calls["args"][0] == ["open", "/tmp/x.pdf"]


def test_open_file_linux(monkeypatch):
    calls = {}
    monkeypatch.setattr(platform.sys, "platform", "linux")
    monkeypatch.setattr(platform.subprocess, "run",
                        lambda *a, **k: calls.setdefault("args", a))
    platform.open_file(Path("/tmp/x.pdf"))
    assert calls["args"][0] == ["xdg-open", "/tmp/x.pdf"]
