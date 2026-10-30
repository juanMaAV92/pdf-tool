import pytest

from pdftool.core import registry
from pdftool.core.plugin import BaseParams, ToolMeta, ToolResult, ToolSpec


def _spec(id_, name="T", order=100):
    return ToolSpec(
        meta=ToolMeta(id=id_, name=name, description="d", category="c", order=order),
        params=BaseParams,
        run=lambda inputs, params, progress=None: ToolResult(outputs=[], summary=""),
    )


def test_register_and_get_specs():
    registry.clear()
    registry.register(_spec("dummy"))
    specs = registry.get_specs()
    assert len(specs) == 1
    assert specs[0].meta.id == "dummy"


def test_registering_the_same_spec_twice_is_harmless():
    registry.clear()
    spec = _spec("same")
    registry.register(spec)
    registry.register(spec)
    assert len(registry.get_specs()) == 1


def test_duplicate_id_from_another_spec_is_rejected():
    registry.clear()
    registry.register(_spec("same", "A"))
    with pytest.raises(ValueError, match="same"):
        registry.register(_spec("same", "B"))


def test_specs_follow_the_declared_order():
    registry.clear()
    registry.register(_spec("c", "Zeta", order=10))
    registry.register(_spec("a", "Alfa", order=30))
    registry.register(_spec("b", "Beta", order=20))
    assert [s.meta.id for s in registry.get_specs()] == ["c", "b", "a"]


def test_a_spec_that_fails_to_import_does_not_break_discovery(tmp_path, monkeypatch):
    pkg = tmp_path / "fake_specs"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "good").mkdir()
    (pkg / "good" / "__init__.py").write_text("")
    (pkg / "good" / "spec.py").write_text(
        "from pdftool.core import registry\n"
        "from pdftool.core.plugin import BaseParams, ToolMeta, ToolSpec\n"
        "SPEC = registry.register(ToolSpec(\n"
        "    meta=ToolMeta(id='good', name='G', description='d', category='c'),\n"
        "    params=BaseParams,\n"
        "    run=lambda inputs, params, progress=None: None,\n"
        "))\n"
    )
    (pkg / "broken").mkdir()
    (pkg / "broken" / "__init__.py").write_text("")
    (pkg / "broken" / "spec.py").write_text(
        "raise ImportError('falta una dependencia')\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry.clear()

    failed = registry.discover("fake_specs")

    assert failed == ["broken"]
    assert [s.meta.id for s in registry.get_specs()] == ["good"]


def test_real_specs_are_ordered_by_task():
    registry.discover()
    ids = [s.meta.id for s in registry.get_specs()]
    expected = ["merge", "split", "compress", "images2pdf", "watermark", "protect"]
    assert [i for i in ids if i in expected] == expected
