from pathlib import Path

import pytest

from pdftool.core.batch import run_batch, validate_inputs
from pdftool.core.jobs import JobCancelled


def _files(tmp_path, *names):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_text("x")
        paths.append(p)
    return paths


def _ok(path, progress):
    progress(1.0, "hecho")
    return path.with_suffix(".out"), f"→ {path.stem}.out"


def test_validate_inputs_rejects_empty():
    with pytest.raises(ValueError, match="inputs está vacío"):
        validate_inputs([])


def test_validate_inputs_rejects_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_inputs([tmp_path / "no.pdf"])


def test_validate_inputs_returns_paths(tmp_path):
    (a,) = _files(tmp_path, "a.pdf")
    assert validate_inputs([str(a)]) == [a]


def test_failure_in_one_file_does_not_stop_the_batch(tmp_path):
    a, b, c = _files(tmp_path, "a.pdf", "b.pdf", "c.pdf")

    def one(path, progress):
        if path == b:
            raise RuntimeError("dañado")
        return _ok(path, progress)

    res = run_batch([a, b, c], one, all_failed="nada")
    assert res.outputs == [a.with_suffix(".out"), c.with_suffix(".out")]
    assert [i.ok for i in res.items] == [True, False, True]
    assert res.items[1].output_path is None
    assert "dañado" in res.items[1].message


def test_cancellation_is_not_swallowed(tmp_path):
    a, b = _files(tmp_path, "a.pdf", "b.pdf")
    seen = []

    def one(path, progress):
        seen.append(path)
        raise JobCancelled()

    with pytest.raises(JobCancelled):
        run_batch([a, b], one, all_failed="nada")
    assert seen == [a]


def test_single_failure_reraises_the_original_error(tmp_path):
    (a,) = _files(tmp_path, "a.pdf")

    def one(path, progress):
        raise KeyError("original")

    with pytest.raises(KeyError, match="original"):
        run_batch([a], one, all_failed="nada")


def test_all_failed_raises_the_given_message(tmp_path):
    a, b = _files(tmp_path, "a.pdf", "b.pdf")

    def one(path, progress):
        raise RuntimeError("x")

    with pytest.raises(ValueError, match="Ningún PDF"):
        run_batch([a, b], one, all_failed="Ningún PDF pudo procesarse.")


def test_progress_is_scoped_per_file(tmp_path):
    a, b = _files(tmp_path, "a.pdf", "b.pdf")
    calls = []
    run_batch([a, b], _ok, lambda p, m: calls.append((p, m)), all_failed="nada")
    assert calls == [(0.5, "[1/2] a.pdf: hecho"), (1.0, "[2/2] b.pdf: hecho")]


def test_single_file_progress_has_no_prefix(tmp_path):
    (a,) = _files(tmp_path, "a.pdf")
    calls = []
    run_batch([a], _ok, lambda p, m: calls.append((p, m)), all_failed="nada")
    assert calls == [(1.0, "hecho")]


def test_paths_are_normalized(tmp_path):
    (a,) = _files(tmp_path, "a.pdf")
    res = run_batch([str(a)], _ok, all_failed="nada")
    assert res.items[0].input_path == Path(a)


def test_failed_item_message_is_human(tmp_path):
    from pdftool.core.errors import UserError

    a, b, c = _files(tmp_path, "a.pdf", "b.pdf", "c.pdf")

    def one(path, progress):
        if path == a:
            raise UserError("Contraseña incorrecta.")
        if path == b:
            raise RuntimeError("code=7: no objects found")
        return _ok(path, progress)

    res = run_batch([a, b, c], one, all_failed="nada")
    assert res.items[0].message == "Contraseña incorrecta."
    assert "no objects found" not in res.items[1].message


def test_all_failed_is_a_user_error(tmp_path):
    from pdftool.core.errors import UserError

    a, b = _files(tmp_path, "a.pdf", "b.pdf")

    def one(path, progress):
        raise RuntimeError("x")

    with pytest.raises(UserError):
        run_batch([a, b], one, all_failed="Ningún PDF pudo procesarse.")
