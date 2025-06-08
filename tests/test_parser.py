from gherkbot.parser import parse_feature
from hypothesis import given
from gherkbot.strategies import feature


@given(content=feature())
def test_parse_feature_property(content: str):
    assert parse_feature(content) is not None


@given(content=feature())
def test_parse_simple_feature_text(content: str):
    assert parse_feature(content) is not None
