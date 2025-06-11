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
    gherkin_ast_data = cast(dict[str, str], gherkin_ast_data_obj)  # type: ignore[reportGeneralTypeIssues]

    # Now proceed with Pydantic validation and the rest of the logic
    parsed_ast = GherkinASTModel.model_validate(gherkin_ast_data)

    if not parsed_ast.feature:
        return ""

    feature = parsed_ast.feature
    feature_name = feature.name
    feature_description = feature.description or ""  # Ensure it's a string

    settings_lines = ["*** Settings ***"]
    settings_lines.append(f"Documentation    Feature: {feature_name}")
    if feature_description:  # No need to check for None if default is ""
        for line in feature_description.strip().split("\n"):
            settings_lines.append(f"...              {line.strip()}")

    keyword_definitions: list[tuple[str, list[str], list[str]]] = []
    test_case_definitions: list[tuple[str, list[str]]] = []

    for child_item in feature.children:
        if child_item.background:
            bg_data = child_item.background
            background_steps_raw: list[StepNodeModel] = []
            if bg_data.steps:
                background_steps_raw = [
                    StepNodeModel(keyword=s.keyword.strip(), text=s.text, docString=s.docString, dataTable=s.dataTable)
                    for s in bg_data.steps
                ]
            if background_steps_raw:
                keyword_definitions.append(
                    (
                        "Run Background Steps",
                        [],
                        _format_robot_steps(background_steps_raw),
                    )
                )
                settings_lines.append("Test Setup       Run Background Steps")

        elif child_item.scenario:
            template_name: str = ""  # Initialize template_name
            scenario = child_item.scenario
            scenario_name = scenario.name
            scenario_keyword_type = scenario.keyword

            if scenario_name:
                if scenario_keyword_type == "Scenario Outline":
                    sanitized_scenario_name = re.sub(
                        r"[^a-zA-Z0-9_]", "_", scenario_name
                    )
                    template_name = f"{sanitized_scenario_name.title()}Template"
                    settings_lines.append(f"Test Template    {template_name}")

                    outline_steps_raw: list[StepNodeModel] = []
                    if scenario.steps:
                        outline_steps_raw = [
                            StepNodeModel(keyword=s.keyword.strip(), text=s.text)
                            for s in scenario.steps
                        ]

                    example_headers: list[str] = []
                    examples_data_rows: list[list[str]] = []
                    if scenario.examples:  # Should be a list
                        for (
                            examples_block
                        ) in scenario.examples:  # Iterate if multiple example blocks
                            if (
                                examples_block.tableHeader
                                and examples_block.tableHeader.cells
                            ):
                                example_headers = [
                                    cell.value
                                    for cell in examples_block.tableHeader.cells
                                ]
                            if examples_block.tableBody:
                                for row_data in examples_block.tableBody:
                                    examples_data_rows.append(
                                        [cell.value for cell in row_data.cells]
                                    )
                            # For simplicity, Robot only supports one Test Template per file effectively,
                            # so we use the headers from the first examples block.
                            # If multiple example blocks have different headers, this might need adjustment.
                            # For now, we assume headers are consistent or only first block's headers matter for template.
                            if example_headers:
                                break  # Use headers from first block with headers

                    if outline_steps_raw:  # Only define template if there are steps
                        keyword_definitions.append(
                            (
                                template_name,
                                example_headers,
                                _format_robot_steps(outline_steps_raw, example_headers),
                            )
                        )

                    for data_row_values in examples_data_rows:
                        example_name_suffix = ", ".join(data_row_values)
                        # Ensure scenario_name (original from Gherkin) is used for test case name
                        tc_name = f"{scenario.name} example for {example_name_suffix}"
                        test_case_definitions.append((tc_name, data_row_values))
                    # This is the end of the "Scenario Outline" specific logic inside "if scenario_name:"

                if scenario_keyword_type == "Scenario":
                    # This block now correctly processes regular Scenarios if scenario_name is true
                    scenario_steps_raw: list[StepNodeModel] = []
                    if scenario.steps:
                        scenario_steps_raw = [
                            StepNodeModel(keyword=s.keyword.strip(), text=s.text, docString=s.docString, dataTable=s.dataTable)
                            for s in scenario.steps
                        ]
                    if scenario_steps_raw:  # Only add test case if there are steps
                        test_case_definitions.append(
                            (scenario_name, _format_robot_steps(scenario_steps_raw))
                        )

    final_output_lines: list[str] = []

    if len(settings_lines) > 1:
        final_output_lines.extend(settings_lines)
        if test_case_definitions or keyword_definitions:
            final_output_lines.append("")

    if test_case_definitions:
        final_output_lines.append("*** Test Cases ***")
        for tc_name, tc_content_or_data in test_case_definitions:
            if tc_content_or_data and tc_content_or_data[0].strip().startswith(
                ("Given", "When", "Then", "And", "But")
            ):  # Regular scenario steps
                final_output_lines.append(tc_name)
                final_output_lines.extend(tc_content_or_data)
            else:  # Scenario outline data row
                data_str = "    ".join(tc_content_or_data)
                final_output_lines.append(f"{tc_name}    {data_str}")
            final_output_lines.append("")
        if final_output_lines and final_output_lines[-1] == "":
            _ = final_output_lines.pop()
        if keyword_definitions:
            final_output_lines.append("")

    if keyword_definitions:
        final_output_lines.append("*** Keywords ***")
        for kw_name, kw_args, kw_steps in keyword_definitions:
            final_output_lines.append(kw_name)
            if kw_args:
                arg_str = "    ".join([f"${{{arg}}}" for arg in kw_args])
                final_output_lines.append(f"    [Arguments]    {arg_str}")
            final_output_lines.extend(kw_steps)
            final_output_lines.append("")
        if final_output_lines and final_output_lines[-1] == "":
            _ = final_output_lines.pop()

    while final_output_lines and final_output_lines[-1] == "":
        _ = final_output_lines.pop()

    return "\n".join(final_output_lines) + "\n" if final_output_lines else ""
