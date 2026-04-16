import uuid
from contextlib import asynccontextmanager
from typing import Literal

from langchain_core.messages import AIMessage, ToolCall
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import SSEConnection
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from sql_graph import common
from sql_graph.state import GlobalState
from sql_graph.tools_node import generate_query_system_prompt, query_check_system, get_schema_tool

mcp_server_config: SSEConnection = {
    "url": "http://127.0.0.1:8000/sse",
    "transport": "sse"
}


@asynccontextmanager
async def make_graph():
    """定义 编译工作流"""
    client = MultiServerMCPClient({'personal': mcp_server_config})
    mcp_tools = await client.get_tools()

    # 所有表名列表的工具
    list_tables_tool = next(tool for tool in mcp_tools if tool.name == 'list_tables_tool')
    # 执行sql的工具
    execute_sql_tool = next(tool for tool in mcp_tools if tool.name == 'db_query_tool')

    def call_tables_node(state: GlobalState):
        """列出所有表名"""
        tool_call: ToolCall = {
            "name": list_tables_tool.name,
            "args": {"query": ""},
            "id": str(uuid.uuid4()),
            "type": "tool_call"
        }
        tool_call_message = AIMessage(content="", tool_calls=[tool_call])
        return {"messages": [tool_call_message]}

    list_tables_node = ToolNode([list_tables_tool], name="list_tables_node")

    def call_get_schema_node(state: GlobalState):
        """调用工具获取表结构"""
        llm_with_tools = common.model.bind_tools([get_schema_tool], tool_choice="any")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    get_schema_node = ToolNode([get_schema_tool], name="get_schema_node")

    def generate_query_node(state: GlobalState):
        """生成SQL查询"""
        system_prompt = {
            "role": "system",
            "content": generate_query_system_prompt
        }
        llm_with_tools = common.model.bind_tools([execute_sql_tool])
        resp = llm_with_tools.invoke([system_prompt] + state["messages"])
        return {"messages": [resp]}

    def check_query_node(state: GlobalState):
        """校验SQL查询"""
        system_prompt = {
            "role": "system",
            "content": query_check_system
        }
        # 上游的SQL查询语句
        tool_call = state["messages"][-1].tool_calls[0]
        user_message = {"role": "user", "content": tool_call["args"]["query"]}
        llm_with_tools = common.model.bind_tools([execute_sql_tool], tool_choice="any")
        resp = llm_with_tools.invoke([system_prompt, user_message])
        resp.id = state["messages"][-1].id

        return {"messages": [resp]}

    def should_continue(state: GlobalState) -> Literal[END, 'check_query_node']:
        """条件路由"""
        messages = state["messages"]
        last_message = messages[-1]
        if not last_message.tool_calls:
            return END
        else:
            return "check_query_node"

    run_query_node = ToolNode([execute_sql_tool], name="run_query_node")

    graph = StateGraph(GlobalState)

    graph.add_node(call_tables_node)  # 列表
    graph.add_node(list_tables_node)
    graph.add_node(call_get_schema_node)  # 获取表结构
    graph.add_node(get_schema_node)  # 执行获取表结构
    graph.add_node(generate_query_node)  # 生成SQL查询
    graph.add_node(check_query_node)  # 校验SQL查询
    graph.add_node(run_query_node)  # 执行SQL查询

    graph.add_edge(START, 'call_tables_node')
    graph.add_edge('call_tables_node', 'list_tables_node')
    graph.add_edge('list_tables_node', 'call_get_schema_node')
    graph.add_edge('call_get_schema_node', 'get_schema_node')
    graph.add_edge('get_schema_node', 'generate_query_node')
    graph.add_conditional_edges(
        'generate_query_node',
        should_continue,
        {
            END: END,
            'check_query_node': 'check_query_node'
        })
    graph.add_edge('check_query_node', 'run_query_node')
    graph.add_edge('run_query_node', 'generate_query_node')

    workflow = graph.compile()
    yield workflow
