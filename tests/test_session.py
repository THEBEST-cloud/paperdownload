from pathlib import Path

from paperdl.session import profile_dir, LAS_HOME


def test_profile_dir_is_under_project(tmp_path):
    p = profile_dir(base=tmp_path)
    assert p == tmp_path / ".profile"


def test_las_home_constant():
    assert LAS_HOME.startswith("https://www.las.ac.cn")
