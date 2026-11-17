import pytest

from nightdesk.cli import main


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "nightdesk" in capsys.readouterr().out


def test_no_args_prints_help(capsys):
    assert main([]) == 0
    assert "usage: nightdesk" in capsys.readouterr().out
