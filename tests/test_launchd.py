from anarlog_exporter import launchd


def test_build_plist_contains_label_and_args():
    plist = launchd.build_plist(interval=42)
    assert plist["Label"] == "com.zaharinea.anarlog-exporter"
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] is True
    args = plist["ProgramArguments"]
    assert "watch" in args
    assert "--interval" in args
    assert "42" in args
    assert "PATH" in plist["EnvironmentVariables"]


def test_build_plist_without_interval():
    plist = launchd.build_plist()
    args = plist["ProgramArguments"]
    assert "--interval" not in args
