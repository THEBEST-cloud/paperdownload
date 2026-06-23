import pytest
from paperdl.search import get_source
from paperdl.search.openalex import OpenAlexSource


def test_get_source_default():
    s = get_source()
    assert isinstance(s, OpenAlexSource)


def test_get_source_unknown():
    with pytest.raises(ValueError):
        get_source("nope")
