import pytest

from anarlog_exporter.session import Session
from anarlog_exporter.template import (
    DEFAULT_TEMPLATE,
    render_filename,
    render_markdown,
)


def _session(make_session) -> Session:
    sdir = make_session()
    s = Session.from_dir(sdir)
    assert s is not None
    return s


def test_render_default_template(make_session):
    session = _session(make_session)
    md = render_markdown(DEFAULT_TEMPLATE, session)
    assert "# Design Review" in md
    assert "session_id: 11111111-2222-3333-4444-555555555555" in md
    assert "date: 2025-12-05" in md
    assert "Главное" in md
    assert "Спикер" in md


def test_render_custom_template(make_session):
    session = _session(make_session)
    tmpl = "# ${title}\n\n${transcript}\n"
    md = render_markdown(tmpl, session)
    assert md.startswith("# Design Review")
    assert "Спикер" in md


def test_render_template_unknown_var(make_session):
    session = _session(make_session)
    with pytest.raises(ValueError, match="неизвестную переменную"):
        render_markdown("${oops}", session)


def test_render_filename_default(make_session):
    session = _session(make_session)
    path = render_filename("{date} - {title}.md", session, "%Y-%m-%d", "%H%M")
    assert str(path) == "2025-12-05 - Design Review.md"


def test_render_filename_with_time_and_subdir(make_session):
    session = _session(make_session)
    path = render_filename(
        "{year}/{month}/{date} {time} - {title}.md", session, "%Y-%m-%d", "%H%M"
    )
    assert str(path) == "2025/12/2025-12-05 1430 - Design Review.md"


def test_render_filename_rejects_traversal(make_session):
    session = _session(make_session)
    with pytest.raises(ValueError, match="небезопасный путь"):
        render_filename("../{title}.md", session, "%Y-%m-%d", "%H%M")


def test_render_filename_unknown_placeholder(make_session):
    session = _session(make_session)
    with pytest.raises(ValueError, match="неизвестный плейсхолдер"):
        render_filename("{foo}.md", session, "%Y-%m-%d", "%H%M")
