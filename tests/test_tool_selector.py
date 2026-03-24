import unittest

from app.services.tool_selector import select_tool_from_prompt


AVAILABLE_TOOLS = [
    {"name": "generate_mvp_plan"},
    {"name": "generate_entities"},
    {"name": "generate_sql_schema"},
    {"name": "suggest_api_endpoints"},
]


class ToolSelectorTests(unittest.TestCase):
    def assert_selected_tool(self, prompt: str, expected_tool: str | None) -> None:
        selection = select_tool_from_prompt(prompt, AVAILABLE_TOOLS)
        if expected_tool is None:
            self.assertIsNone(selection)
            return

        self.assertIsNotNone(selection)
        self.assertEqual(expected_tool, selection["tool"])

    def test_routes_mvp_requests_to_generate_mvp_plan(self) -> None:
        self.assert_selected_tool(
            "Cria um plano MVP curto para uma aplicação de gestão de tarefas para estudantes.",
            "generate_mvp_plan",
        )

    def test_routes_entity_modelling_requests_to_generate_entities(self) -> None:
        self.assert_selected_tool(
            "Modela as entidades principais para uma aplicação de gestão de tarefas para estudantes.",
            "generate_entities",
        )

    def test_routes_explicit_sql_requests_to_generate_sql_schema(self) -> None:
        self.assert_selected_tool(
            "Cria a base de dados SQL para um sistema de tarefas com utilizadores e projetos.",
            "generate_sql_schema",
        )

    def test_routes_api_requests_to_suggest_api_endpoints(self) -> None:
        self.assert_selected_tool(
            "Sugere endpoints para uma API de gestão de tarefas.",
            "suggest_api_endpoints",
        )

    def test_conceptual_tables_still_route_to_entities(self) -> None:
        self.assert_selected_tool(
            "Modela tabelas conceptuais e relações principais para o domínio de gestão de tarefas.",
            "generate_entities",
        )

    def test_neutral_fallback_does_not_default_to_sql(self) -> None:
        self.assert_selected_tool(
            "Preciso de ajuda para uma aplicação de gestão de tarefas para estudantes.",
            None,
        )


if __name__ == "__main__":
    unittest.main()
