import asyncio

from sql_graph.draw_png import draw_graph
from sql_graph.text2sql_graph import make_graph


async def main():
    async with make_graph() as workflow:
        draw_graph(workflow, "graph.png")
        while True:
            user_input = input("用户：")
            if user_input.lower() in ["exit", "quit", 'q']:
                print('对话结束')
                break
            else:
                async for event in workflow.astream({"messages": [("user", user_input)]}, stream_mode="values"):
                    event['messages'][-1].pretty_print()


if __name__ == '__main__':
    asyncio.run(main())
