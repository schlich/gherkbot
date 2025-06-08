from gherkin import Parser
from gherkin.errors import CompositeParserException


def parse_feature(content: str):
    "TODO: Investigate how we most smoothly want to handle Gherkin parse errors."
    try:
        return Parser().parse(content)
    except CompositeParserException:
        return None
