from app.config import get_settings


def explain_recommendation(recommendation: dict, question: str) -> dict:
    """Optional constrained agent: supplied facts only; it has no cloud execution tools."""
    settings = get_settings()
    if not settings.openai_api_key:
        return {"mode": "disabled", "message": "Set REDBRIDGE_OPENAI_API_KEY to enable the explanation agent."}
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f'''You are a FinOps explanation assistant. Use only the supplied evidence.
Never invent prices, metrics, cloud capabilities, or approvals. Do not recommend execution.
State assumptions, uncertainties, and the next human verification step.

Recommendation: {recommendation}
Question: {question}'''
    response = client.responses.create(model=settings.openai_model, input=prompt)
    return {"mode": "agent", "answer": response.output_text,
            "boundary": "Explanation only; no provider credentials or execution tools were made available."}

