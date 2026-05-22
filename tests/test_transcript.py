from anarlog_exporter.transcript import build_transcript, format_timestamp


def test_format_timestamp():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(65_000) == "01:05"
    assert format_timestamp(3_725_000) == "62:05"


def test_build_transcript_groups_by_channel():
    data = {
        "transcripts": [
            {
                "started_at": 0,
                "words": [
                    {"channel": 0, "start_ms": 0, "end_ms": 500, "text": "Привет."},
                    {"channel": 0, "start_ms": 600, "end_ms": 1000, "text": " Я начну."},
                    {"channel": 1, "start_ms": 1100, "end_ms": 1500, "text": "Окей."},
                ],
            }
        ]
    }
    result = build_transcript(data)
    assert "**[00:00] Спикер 1:** Привет. Я начну." in result
    assert "**[00:01] Спикер 2:** Окей." in result


def test_build_transcript_splits_on_long_pause():
    data = {
        "transcripts": [
            {
                "started_at": 0,
                "words": [
                    {"channel": 0, "start_ms": 0, "end_ms": 500, "text": "Раз."},
                    {"channel": 0, "start_ms": 5000, "end_ms": 5500, "text": "Два."},
                ],
            }
        ]
    }
    result = build_transcript(data)
    lines = result.split("\n\n")
    assert len(lines) == 2
    assert lines[0].startswith("**[00:00]")
    assert lines[1].startswith("**[00:05]")


def test_build_transcript_empty():
    assert build_transcript({"transcripts": []}) == ""
    assert build_transcript({}) == ""
