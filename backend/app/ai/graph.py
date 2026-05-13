"""
LangGraph pipeline factory.

build_pipeline(ai_client) returns a compiled StateGraph that executes:

  START → intent_validator
        → (if valid) analyzer  [body + garment in parallel via asyncio.gather]
        → review_retriever
        → recommendation_generator
        → risk_evaluator
        → turkish_formatter → END
        → (if invalid) END  (pipeline_error set)
"""

from langgraph.graph import END, START, StateGraph

from app.ai.nodes import (
    intent_validator_node,
    make_analyzer_node,
    recommendation_generator_node,
    review_retriever_node,
    risk_evaluator_node,
    turkish_formatter_node,
)
from app.ai.state import PipelineState


def _route_after_intent(state: PipelineState) -> str:
    return "analyzer" if state.get("intent_valid") else END


def build_pipeline(ai_client):
    """
    Compile a fresh LangGraph pipeline bound to the given ai_client.

    ai_client must implement AIClient protocol (MockAIClient or RealGeminiClient).
    """
    workflow = StateGraph(PipelineState)

    workflow.add_node("intent_validator",          intent_validator_node)
    workflow.add_node("analyzer",                  make_analyzer_node(ai_client))
    workflow.add_node("review_retriever",          review_retriever_node)
    workflow.add_node("recommendation_generator",  recommendation_generator_node)
    workflow.add_node("risk_evaluator",            risk_evaluator_node)
    workflow.add_node("turkish_formatter",         turkish_formatter_node)

    workflow.add_edge(START, "intent_validator")
    workflow.add_conditional_edges("intent_validator", _route_after_intent)
    workflow.add_edge("analyzer",                 "review_retriever")
    workflow.add_edge("review_retriever",         "recommendation_generator")
    workflow.add_edge("recommendation_generator", "risk_evaluator")
    workflow.add_edge("risk_evaluator",           "turkish_formatter")
    workflow.add_edge("turkish_formatter",        END)

    return workflow.compile()
