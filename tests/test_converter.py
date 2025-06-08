import pytest

from gherkbot.converter import (
    convert_ast_to_robot,
    GherkinASTModel,
    FeatureModel,
    ChildModel,
    ScenarioModel,
    StepDetailModel,
    LocationModel,
)



@pytest.fixture
def simple_feature_ast() -> GherkinASTModel:
    return GherkinASTModel(
        feature=FeatureModel(
            location=LocationModel(line=1, column=1),
            language="en",
            keyword="Feature",
            name="Basic Test",
            description="  As a user\n  I want to do something\n  So that I get a result",
            children=[
                ChildModel(
                    scenario=ScenarioModel(
                        location=LocationModel(line=3, column=5),
                        keyword="Scenario",
                        name="A simple scenario",
                        steps=[
                            StepDetailModel(location=LocationModel(line=4, column=7), keyword="Given ", text="a step"),
                            StepDetailModel(location=LocationModel(line=5, column=7), keyword="When ", text="another step"),
                            StepDetailModel(location=LocationModel(line=6, column=7), keyword="Then ", text="a final step"),
                        ],
                    )
                )
            ],
        ),
        comments=[],
    )


def test_convert_simple_feature_to_robot(simple_feature_ast: GherkinASTModel):
    expected_robot_output = """*** Settings ***
Documentation    Feature: Basic Test
...              As a user
...              I want to do something
...              So that I get a result

*** Test Cases ***
A simple scenario
    Given a step
    When another step
    Then a final step
"""
    actual_robot_output = convert_ast_to_robot(simple_feature_ast.model_dump(exclude_none=True))
    assert actual_robot_output.strip() == expected_robot_output.strip()


@pytest.fixture
def feature_with_background_ast() -> object:
    return {
        "feature": {
            "location": {"line": 1, "column": 1},
            "language": "en",
            "keyword": "Feature",
            "name": "Feature with Background",
            "description": "",
            "children": [
                {
                    "background": {
                        "location": {"line": 3, "column": 5},
                        "keyword": "Background",
                        "name": "",
                        "steps": [
                            {"location": {"line": 4, "column": 7}, "keyword": "Given ", "text": "a global setup"},
                            {"location": {"line": 5, "column": 7}, "keyword": "And ", "text": "another global setup step"},
                        ],
                    }
                },
                {
                    "scenario": {
                        "location": {"line": 7, "column": 5}, # Adjusted line based on structure
                        "keyword": "Scenario",
                        "name": "First scenario",
                        "steps": [
                            {"location": {"line": 9, "column": 7}, "keyword": "When ", "text": "I do something"},
                            {"location": {"line": 10, "column": 7}, "keyword": "Then ", "text": "I expect something"},
                        ],
                    }
                },
            ],
        },
        "comments": [],
    }


def test_convert_feature_with_background(feature_with_background_ast: object):
    expected_robot_output = """*** Settings ***
Documentation    Feature: Feature with Background
Test Setup       Run Background Steps

*** Test Cases ***
First scenario
    When I do something
    Then I expect something

*** Keywords ***
Run Background Steps
    Given a global setup
    And another global setup step
"""
    actual_robot_output = convert_ast_to_robot(feature_with_background_ast)
    assert actual_robot_output.strip() == expected_robot_output.strip()


@pytest.fixture
def scenario_outline_feature_ast() -> object:
    return {
        "feature": {
            "location": {"line": 1, "column": 1},
            "language": "en",
            "keyword": "Feature",
            "name": "Scenario Outline Example",
            "description": "",
            "children": [
                {
                    "scenario": {
                        "location": {"line": 3, "column": 5},
                        "keyword": "Scenario Outline",
                        "name": "eating",
                        "steps": [
                            {
                                'location': {'line': 4, 'column': 7},
                                "keyword": "Given ",
                                "text": "there are <start> cucumbers",
                            },
                            {"location": {'line': 5, 'column': 7}, "keyword": "When ", "text": "I eat <eat> cucumbers"},
                            {
                                'location': {'line': 6, 'column': 7},
                                "keyword": "Then ",
                                "text": "I should have <left> cucumbers",
                            },
                        ],
                        "examples": [
                            {
                                'location': {'line': 8, 'column': 9},
                                "keyword": "Examples",
                                "name": "",
                                'tableHeader': {
                                    'location': {'line': 9, 'column': 11},
                                    "cells": [
                                        {"location": {"line": 10, "column": 13}, "value": "start"},
                                        {"location": {"line": 10, "column": 13}, "value": "eat"},
                                        {"location": {"line": 10, "column": 13}, "value": "left"}
                                    ]
                                },
                                'tableBody': [
                                    {
                                        'location': {'line': 12, 'column': 11},
                                        'cells': [
                                            {'location': {'line': 13, 'column': 13}, 'value': '12'},
                                            {'location': {'line': 13, 'column': 13}, 'value': '5'},
                                            {'location': {'line': 13, 'column': 13}, 'value': '7'}
                                        ]
                                    },
                                    {
                                        "location": {"line": 15, "column": 11},
                                        "cells": [
                                            {"location": {"line": 16, "column": 13}, "value": "20"},
                                            {"location": {"line": 16, "column": 13}, "value": "5"},
                                            {"location": {"line": 16, "column": 13}, "value": "15"}
                                        ]
                                    },
                                ],
                            }
                        ],
                    }
                }
            ],
        },
        "comments": [],
    }


def test_convert_scenario_outline_to_robot(
    scenario_outline_feature_ast: object,
):
    expected_robot_output = """*** Settings ***
Documentation    Feature: Scenario Outline Example
Test Template    EatingTemplate

*** Test Cases ***
eating example for 12, 5, 7    12    5    7

eating example for 20, 5, 15    20    5    15

*** Keywords ***
EatingTemplate
    [Arguments]    ${start}    ${eat}    ${left}
    Given there are ${start} cucumbers
    When I eat ${eat} cucumbers
    Then I should have ${left} cucumbers
"""
    actual_robot_output = convert_ast_to_robot(scenario_outline_feature_ast)
    assert actual_robot_output.strip() == expected_robot_output.strip()
