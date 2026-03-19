from prompts.planner_system_prompt import planner_system_prompt


planner_prompt = """
{system_prompt}

Ideia do utilizador:
{idea}
""".strip()


def build_planner_prompt(idea: str) -> str:
    return planner_prompt.format(
        system_prompt=planner_system_prompt,
        idea=idea.strip(),
    )
