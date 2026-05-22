import json

from anarlog_exporter.state import INDEX_FILENAME, Index


def test_index_load_missing(tmp_path):
    idx = Index.load(tmp_path)
    assert idx.exported == {}
    assert not idx.contains("anything")


def test_index_load_corrupted_returns_empty(tmp_path):
    (tmp_path / INDEX_FILENAME).write_text("not json at all {", encoding="utf-8")
    idx = Index.load(tmp_path)
    assert idx.exported == {}


def test_index_add_save_load_roundtrip(tmp_path):
    idx = Index.load(tmp_path)
    idx.add("sid-1", "2026-04-09 - Meeting.md")
    idx.add("sid-2", "2026-04-10/note.md")
    idx.save()

    raw = json.loads((tmp_path / INDEX_FILENAME).read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert set(raw["exported"]) == {"sid-1", "sid-2"}
    assert raw["exported"]["sid-1"]["filename"] == "2026-04-09 - Meeting.md"
    assert "exported_at" in raw["exported"]["sid-1"]

    reloaded = Index.load(tmp_path)
    assert reloaded.contains("sid-1")
    assert reloaded.exported["sid-2"]["filename"] == "2026-04-10/note.md"


def test_index_remove(tmp_path):
    idx = Index.load(tmp_path)
    idx.add("sid-1", "a.md")
    idx.remove("sid-1")
    idx.remove("never-existed")  # не должно падать
    assert not idx.contains("sid-1")
