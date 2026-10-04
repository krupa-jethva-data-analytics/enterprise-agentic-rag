from typing import TypedDict, List, Dict, Annotated
import operator

class AgentsState(TypedDict):
    messages: Annotated[List[Dict], operator.add]
    current_query: str
    documents: List[str]
    plan: List[str]
    status: str
    final_answer: str

