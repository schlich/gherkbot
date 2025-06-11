import re
from typing import cast
from pydantic import BaseModel, Field

# Pydantic Model Definitions for Gherkin AST


class LocationModel(BaseModel):
    line: int
    column: int


class CellModel(BaseModel):
    location: LocationModel
    value: str


class TableRowModel(BaseModel):
    location: LocationModel
    cells: list[CellModel]


class DocStringModel(BaseModel):
    location: LocationModel
    content: str
    contentType: str | None = None
    delimiter: str # Typically """ or ```

class DataTableModel(BaseModel):
    location: LocationModel
    rows: list[TableRowModel]

class StepDetailModel(
    BaseModel
):  # Represents 's' in list comprehensions from input AST
    location: LocationModel
    keyword: str
    text: str
    docString: DocStringModel | None = None
    dataTable: DataTableModel | None = None


class StepNodeModel(BaseModel):  # Simplified structure for _format_robot_steps
    keyword: str
    text: str
    docString: DocStringModel | None = None
    dataTable: DataTableModel | None = None


class ExamplesModel(BaseModel):
    location: LocationModel
    keyword: str
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    tableHeader: TableRowModel
    tableBody: list[TableRowModel]


class BackgroundModel(BaseModel):
    location: LocationModel
    keyword: str
    name: str = ""
    description: str = ""
    steps: list[StepDetailModel] = Field(default_factory=list)


class ScenarioModel(BaseModel):
    location: LocationModel
    keyword: str  # 'Scenario' or 'Scenario Outline'
    name: str
    description: str = ""
    steps: list[StepDetailModel] = Field(default_factory=list)
    examples: list[ExamplesModel] = Field(
        default_factory=list
    )  # Only for Scenario Outlines
    tags: list[str] = Field(default_factory=list)


class ChildModel(BaseModel):
    background: BackgroundModel | None = None
    scenario: ScenarioModel | None = None


class FeatureModel(BaseModel):
    tags: list[str] = Field(default_factory=list)
    location: LocationModel
    language: str = "en"  # Default language if not specified
    keyword: str
    name: str
    description: str = ""
    children: list[ChildModel] = Field(default_factory=list)


class GherkinASTModel(BaseModel):
    feature: FeatureModel | None = None  # Make feature itself optional at top level
    comments: list[str] = Field(default_factory=list)


# Rebuild models to resolve forward references
_ = LocationModel.model_rebuild()
_ = CellModel.model_rebuild()
_ = TableRowModel.model_rebuild()
_ = DocStringModel.model_rebuild()
_ = DataTableModel.model_rebuild()

_ = StepDetailModel.model_rebuild()
_ = ExamplesModel.model_rebuild()
_ = BackgroundModel.model_rebuild()
_ = ScenarioModel.model_rebuild()
_ = ChildModel.model_rebuild()
_ = FeatureModel.model_rebuild()
_ = GherkinASTModel.model_rebuild()


def _format_robot_steps(
    steps: list[StepNodeModel], arg_names: list[str] | None = None
) -> list[str]:
    formatted_steps: list[str] = []
    for step_data in steps:
        keyword = step_data.keyword.strip()
        text = step_data.text
        if arg_names:  # For scenario outline steps, replace placeholders
            for arg_name in arg_names:
                text = re.sub(f"<{re.escape(arg_name)}>", f"${{{arg_name}}}", text)
        formatted_steps.append(f"    {keyword} {text}")

        if step_data.docString:
            doc_string_content = step_data.docString.content
            for line in doc_string_content.splitlines():
                formatted_steps.append(f"    ...    {line}")
        if step_data.dataTable:
            for row in step_data.dataTable.rows:
                cell_values = [cell.value for cell in row.cells]
                formatted_steps.append(f"    ...    | {' | '.join(cell_values)} |")
    return formatted_steps


def convert_ast_to_robot(gherkin_ast_data_obj: object) -> str:
    if not gherkin_ast_data_obj:
        return ""
    gherkin_ast_data = cast(dict[str, str], gherkin_ast_data_obj)

    try:
        gherkin_ast = GherkinASTModel.model_validate(gherkin_ast_data)
    except Exception:
        return ""

    if not gherkin_ast.feature:
        return ""

    feature = gherkin_ast.feature
    unique_keywords = set()

    # --- Settings Section ---
    settings_lines = ["*** Settings ***"]
    doc_parts = [f"Feature: {feature.name}"]
    if feature.description:
        doc_parts.extend([line.strip() for line in feature.description.strip().split("\n")])

    if len(doc_parts) > 1:
        # Join with ... and correct indentation for multi-line descriptions
        formatted_doc = f"{doc_parts[0]}\n...    " + "\n...    ".join(doc_parts[1:])
        settings_lines.append(f"Documentation    {formatted_doc}")
    else:
        settings_lines.append(f"Documentation    {doc_parts[0]}")

    # --- Data Collection ---
    test_case_definitions = []
    keyword_definitions = []

    has_background = any(c.background for c in feature.children)
    if has_background:
        settings_lines.append("Test Setup       Run Background Steps")

    for child_item in feature.children:
        # --- Background ---
        if child_item.background:
            bg_data = child_item.background
            for step in bg_data.steps:
                unique_keywords.add(step.text)
            background_steps_raw = [StepNodeModel.model_validate(s.model_dump()) for s in bg_data.steps]
            keyword_definitions.append(("Run Background Steps", None, _format_robot_steps(background_steps_raw)))

        # --- Scenarios ---
        if child_item.scenario:
            scenario = child_item.scenario
            for step in scenario.steps:
                unique_keywords.add(step.text)

            if scenario.keyword == "Scenario":
                scenario_steps_raw = [StepNodeModel.model_validate(s.model_dump()) for s in scenario.steps]
                test_case_definitions.append((scenario.name, _format_robot_steps(scenario_steps_raw)))

            elif scenario.keyword == "Scenario Outline":
                template_name = f"{scenario.name} Template"
                settings_lines.append(f"Test Template    {template_name}")

                example_headers = []
                if scenario.examples and scenario.examples[0].tableHeader:
                    example_headers = [c.value for c in scenario.examples[0].tableHeader.cells]

                outline_steps_raw = [StepNodeModel.model_validate(s.model_dump()) for s in scenario.steps]
                keyword_definitions.append((template_name, example_headers, _format_robot_steps(outline_steps_raw, example_headers)))

                for examples_block in scenario.examples:
                    for row in examples_block.tableBody:
                        data_row_values = [c.value for c in row.cells]
                        test_case_definitions.append((f"{scenario.name} - {', '.join(data_row_values)}", data_row_values))

    # --- Assemble Final Output ---
    final_output_lines = []
    if len(settings_lines) > 1:
        final_output_lines.extend(settings_lines)
        final_output_lines.append("")

    if test_case_definitions:
        final_output_lines.append("*** Test Cases ***")
        for tc_name, tc_content in test_case_definitions:
            is_regular_scenario = any(line.strip().startswith(("Given", "When", "Then", "And", "But")) for line in tc_content)
            if is_regular_scenario:
                final_output_lines.append(tc_name)
                final_output_lines.extend(tc_content)
            else: # It's an outline, content is just data
                final_output_lines.append(f"{tc_name}    {'    '.join(tc_content)}")
            final_output_lines.append("")

    if keyword_definitions or unique_keywords:
        final_output_lines.append("*** Keywords ***")

    if keyword_definitions:
        for kw_name, kw_args, kw_steps in keyword_definitions:
            final_output_lines.append(kw_name)
            if kw_args:
                final_output_lines.append(f"    [Arguments]    {'    '.join([f'${{{arg}}}' for arg in kw_args])}")
            final_output_lines.extend(kw_steps)
            final_output_lines.append("")

    if unique_keywords:
        defined_keywords = {kw[0] for kw in keyword_definitions}
        for keyword in sorted(list(unique_keywords)):
            if keyword not in defined_keywords:
                final_output_lines.append(keyword)
                final_output_lines.append(f'    # TODO: implement keyword "{keyword}".')
                final_output_lines.append("    Fail    Not Implemented")
                final_output_lines.append("")

    while final_output_lines and final_output_lines[-1] == "":
        final_output_lines.pop()

    return "\n".join(final_output_lines) + "\n" if final_output_lines else ""
