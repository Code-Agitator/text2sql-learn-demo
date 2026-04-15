from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class GlobalState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
