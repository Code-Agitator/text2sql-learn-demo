import uuid
from contextlib import asynccontextmanager

from langchain_core.messages import AIMessage, ToolCall
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import SSEConnection
from langgraph.prebuilt import ToolNode

from sql_graph import common
from sql_graph.state import GlobalState
from sql_graph.tools_node import generate_query_system_prompt, query_check_system

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

    def list_tables_node(state: GlobalState):
        """列出所有表面"""
        tool_call: ToolCall = {
            "name": list_tables_tool.name,
            "args": {},
            "id": str(uuid.uuid4()),
            "type": "tool_call"
        }

        tool_call_message = AIMessage(content="", tool_calls=[tool_call])
        tool_message = list_tables_tool.invoke(tool_call)
        response = AIMessage(content=f"所有可用的表:{tool_message.content}")
        return {"messages": [tool_call_message, tool_message, response]}

    def get_schema_node(state: GlobalState):
        """调用工具获取表结构"""
        llm_with_tools = common.model.bind_tools([get_schema_node], tool_choice="any")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

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

    run_query_node = ToolNode([execute_sql_tool], name="run_query")

    # TODO
    pass
