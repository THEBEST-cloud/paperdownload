from paperdl.cli import build_parser


def test_parser_login():
    args = build_parser().parse_args(["login"])
    assert args.command == "login"


def test_parser_run_requires_list():
    args = build_parser().parse_args(["run", "mylist.txt"])
    assert args.command == "run"
    assert args.list == "mylist.txt"


def test_parser_run_max_option():
    args = build_parser().parse_args(["run", "l.txt", "--max", "10"])
    assert args.max == 10


def test_parser_retry():
    args = build_parser().parse_args(["retry"])
    assert args.command == "retry"


def test_parser_run_show_flag():
    args = build_parser().parse_args(["run", "l.txt", "--show"])
    assert args.show is True


def test_parser_run_defaults_no_show():
    args = build_parser().parse_args(["run", "l.txt"])
    assert args.show is False
