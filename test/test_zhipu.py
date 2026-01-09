import time
from zai import ZhipuAiClient
api_key="b7e5d92e4cd661d4eafa7737ec2253fd.aBhndS6s6z6VB2O6"
# client = ZhipuAiClient(api_key="b7e5d92e4cd661d4eafa7737ec2253fd.aBhndS6s6z6VB2O6")
# st = time.time()
# response = client.web_search.web_search(
#    search_engine="search_pro_quark",
#    search_query="今日纳斯达克指数，2025年12月23日",
#    count=3,  # 返回结果的条数，范围1-50，默认10
#    search_domain_filter="www.sohu.com",  # 只访问指定域名的内容
#    search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
#    content_size="medium"  # 控制网页摘要的字数，默认medium
# )
# et = time.time()
# print(response)
# print(et - st)


import requests

url = "https://open.bigmodel.cn/api/paas/v4/web_search"
query = "今日上海天气"

payload = {
    "search_query": f"{query}",
    "search_engine": "search_std",
    "search_intent": False,
    "count": 5,
    "search_domain_filter": "search_std",
    "search_recency_filter": "noLimit",
    "content_size": "medium",
    "request_id": "dongyuqi123",
    "user_id": "dongyuqi"
}
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

st = time.time()
response = requests.post(url, json=payload, headers=headers)
et = time.time()

print(response.text)
print(et - st)