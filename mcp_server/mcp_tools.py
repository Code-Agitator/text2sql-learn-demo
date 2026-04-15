from fastmcp.server import FastMCP

from sql_graph.common import web_search_tool
from sql_graph.tools_node import db

server = FastMCP(
    name="My Server",
    instructions="A simple server",
    port=8000
)


@server.tool('my_search_tool', description='专门搜索互联网中的内容')
def my_search(query: str) -> str:
    """搜索互联网上的内容"""
    try:
        docs = web_search_tool.invoke({"query": query})  # 调用网络搜索工具
        if docs:
            return "\n".join([d["content"] for d in docs])
    except Exception as e:
        print(e)
        return '没有搜索到任何内容！'


@server.tool('list_tables_tool',
             description='输入是一个空字符串，返回数据库中的所有表名，以逗号分割')
def list_tables_tool(query: str) -> str:
    return ",".join(db.get_usable_table_names())


@server.tool('db_query_tool', description='输入是一个SQL查询，返回查询结果。如果查询失败请检查查询语句修改后重试')
def db_query_tool(query: str) -> str:
    result = db.run_no_throw(query)
    if not result:
        return '错误:查询失败。请修改查询语句重试'
    return result


if __name__ == '__main__':
    server.run()
