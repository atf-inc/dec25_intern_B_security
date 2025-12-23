from langgraph.graph import StateGraph, END
from apps.worker.intent.schemas import EmailIntentState
from apps.worker.intent.nodes import analyze_subject, analyze_body, resolve_intent

def create_intent_graph():
    workflow = StateGraph(EmailIntentState)
    
    workflow.add_node("analyze_subject", analyze_subject)
    workflow.add_node("analyze_body", analyze_body)
    workflow.add_node("resolve_intent", resolve_intent)
    
    workflow.set_entry_point("analyze_subject")
    
    workflow.add_edge("analyze_subject", "analyze_body")
    workflow.add_edge("analyze_body", "resolve_intent")
    workflow.add_edge("resolve_intent", END)
    
    return workflow.compile()

# Singleton instance
intent_agent = create_intent_graph()
