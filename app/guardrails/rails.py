import logfire

from langchain_groq import ChatGroq
from nemoguardrails import RailsConfig, LLMRails

from app.config import Settings
from app.guardrails.colang_rules import (
    COLANG_CONTENT,
    YAML_CONTENT,
)


_rails: LLMRails | None = None


def initialize_rails() -> None:
    global _rails

    # Separate model used only by NeMo Guardrails
    guard_llm = ChatGroq(
        api_key=Settings.GROQ_API_KEY,
        model="openai/gpt-oss-20b",
        temperature=0
    )

    config = RailsConfig.from_content(
        colang_content=COLANG_CONTENT,
        yaml_content=YAML_CONTENT
    )

    _rails = LLMRails(
        config,
        llm=guard_llm
    )

    logfire.info(
        "🛡️ NeMo Guardrails initialised (openai/gpt-oss-20b)."
    )


def guard(message: str) -> tuple[bool, str | None]:

    if _rails is None:
        logfire.warning(
            "⚠️ Guardrails not initialised — skipping gate."
        )
        return False, None

    with logfire.span("🛡️ Guardrails Check"):

        result = _rails.generate(
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ],
            options={
                "rails": ["input"],
                "log": {
                    "activated_rails": True
                }
            }
        )

        print("\n========== GUARDRAIL DEBUG ==========")
        print("USER INPUT:", message)

        # Debug information
        activated_rails = []

        if hasattr(result, "log") and result.log:
            activated_rails = result.log.activated_rails or []

        print("ACTIVATED RAILS:", activated_rails)

        # Check whether the input rail blocked the request
        for rail in activated_rails:

            if rail.type == "input":

                for action in rail.executed_actions:

                    decision = action.return_value.decision

                    print("INPUT RAIL DECISION:", decision)

                    if str(decision).lower().endswith("block"):

                        print("🛡️ GUARD FIRED: BLOCKED")
                        print("====================================")

                        return (
                            True,
                            "I'm an Enterprise IT Assistant focused on Kubernetes, Intel hardware, and networking. I can't help with that — but ask me anything technical!"
                        )

        print("✅ GUARD PASSED")
        print("====================================")

        return False, None