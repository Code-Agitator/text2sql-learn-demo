import os

import dotenv
from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()
model = ChatOpenAI(
    model='deepseek-ai/DeepSeek-V3.2',
    base_url=os.environ.get('OPENAI_BASE_URL'),
    api_key=os.environ.get('OPENAI_API_KEY')
)

web_search_tool = TavilySearchResults(max_results=2, tavily_api_key=os.environ.get('TAVILY_API_KEY'))
