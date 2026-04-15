from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from sql_graph import common

db = SQLDatabase.from_uri('sqlite:///../chinook.db')
toolkit = SQLDatabaseToolkit(db=db, llm=common.model)
tools = toolkit.get_tools()

get_schema_tool = next(tool for tool in tools if tool.name == 'sql_db_schema')

generate_query_system_prompt = """
你是一个设计用于与SQL数据库交互的智能体。
给定一个输入问题，创建一个语法正确的{dialect}查询来运行，
然后查看查询结果并返回答案。除非用户明确指定他们希望获取的示例数量，
否则始终将查询限制为最多{top_k}个结果。

你可以按相关列对结果进行排序，以返回数据库中最有趣的示例。
永远不要查询特定表的所有列，只询问与问题相关的列。

不要对数据库执行任何DML语句（INSERT、UPDATE、DELETE、DROP等）。
""".format(
    dialect=db.dialect,
    top_k=5,
)



query_check_system = """您是一位注重细节的SQL专家。
请仔细检查SQLite查询中的常见错误，包括：
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

如果发现上述任何错误，请重写查询。如果没有错误，请原样返回查询语句。

检查完成后，您将调用适当的工具来执行查询。"""