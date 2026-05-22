from anarlog_exporter.session import (
    Session,
    clean_content,
    get_note_position,
    sanitize_filename,
    strip_frontmatter,
)


def test_sanitize_filename():
    assert sanitize_filename("a/b:c") == "a-b-c"
    assert sanitize_filename('Q?".md') == "Q--.md"


def test_strip_frontmatter():
    md = "---\nfoo: bar\n---\n\nbody"
    assert strip_frontmatter(md) == "body"
    assert strip_frontmatter("no frontmatter") == "no frontmatter"


def test_clean_content_strips_nbsp():
    md = "---\nfoo: bar\n---\n\nLine 1\n&nbsp;\nLine 2"
    assert clean_content(md) == "Line 1\nLine 2"


def test_get_note_position_in_frontmatter():
    md = "---\nposition: 3\nother: x\n---\n\ntext"
    assert get_note_position(md) == 3


def test_get_note_position_missing():
    assert get_note_position("no frontmatter at all") == 99


def test_session_from_dir(make_session):
    sdir = make_session(
        extra_notes=[("summary", 1, "## Summary\nIt was good."), ("actions", 2, "Action: do X")],
    )
    session = Session.from_dir(sdir)
    assert session is not None
    assert session.title == "Design Review"
    assert session.session_id == "11111111-2222-3333-4444-555555555555"
    assert "It was good" in session.extra_notes[0]
    assert "do X" in session.extra_notes[1]
    assert "Главное" in session.memo
    assert "Спикер" in session.transcript
    assert session.has_content()
