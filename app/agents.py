from app.config import get_settings


def explain_recommendation(recommendation: dict, question: str, agent_config: dict | None = None) -> dict:
    """Optional constrained agent: supplied facts only; it has no cloud execution tools."""
    settings = get_settings()
    if not agent_config and not settings.openai_api_key:
        return {"mode": "disabled", "message": "Set REDBRIDGE_OPENAI_API_KEY to enable the explanation agent."}
    provider = (agent_config or {}).get("provider", "openai")
    api_key = (agent_config or {}).get("api_key", settings.openai_api_key)
    model = (agent_config or {}).get("model", settings.openai_model)
    prompt = f'''You are a FinOps explanation assistant. Use only the supplied evidence.
Never invent prices, metrics, cloud capabilities, or approvals. Do not recommend execution.
State assumptions, uncertainties, and the next human verification step.

Recommendation: {recommendation}
Question: {question}'''
    if provider == "openai":
        from openai import OpenAI
        answer = OpenAI(api_key=api_key).responses.create(model=model, input=prompt).output_text
    elif provider == "anthropic":
        from anthropic import Anthropic
        response = Anthropic(api_key=api_key).messages.create(model=model, max_tokens=1200,
            messages=[{"role": "user", "content": prompt}])
        answer = "".join(block.text for block in response.content if block.type == "text")
    else:
        return {"mode": "disabled", "message": f"Unsupported agent provider: {provider}"}
    return {"mode": "agent", "provider": provider, "model": model, "answer": answer,
            "boundary": "Explanation only; no provider credentials or execution tools were made available."}

