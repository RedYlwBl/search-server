import time
import requests
import json
import logging
from datetime import datetime


# ========== 基础配置 ==========
URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"
API_KEY = "bce-v3/ALTAK-BTanKaPjRoEfcyCtkVfDq/329a9a79884358d01ee383eef7254abf373244cb"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

# ========== 测试问题集 ==========
# TEST_QUERIES = [
#     {"type": "新闻", "query": "今天有什么重要新闻"},
#     {"type": "天气", "query": "今天北京天气怎么样"},
#     {"type": "指数", "query": "今日纳斯达克指数"},
#     {"type": "百科", "query": "全国有多少个码头"},
# ]

TEST_QUERIES = [
{"type": "", "query": "今天钦州的天气怎么样啊（今日日期：2025年12月24日）"},

# {"type": "","query": "最近钦州会下雨吗（今日日期：2025年12月24日）"},

# {"type": "","query": "最近钦州这边还会有台风吗（今日日期：2025年12月24日）"},

# {"type": "","query": "全国一共有多少个自动化码头（今日日期：2025年12月24日）"},

# {"type": "","query": "广州港2024年吞吐量"},

# {"type": "","query": "习近平总书记什么时候来的北部湾港"},

# {"type": "","query": "习总习近平总书记是什么时候考察广西的呀"},

# {"type": "","query": "股市大盘（今日日期：2025年12月24日）"},
    
]

# ========== 日志配置 ==========
log_filename = f"web_search_test_baidu.log"
logging.basicConfig(
    filename=log_filename,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

def call_web_search(query: str) -> float:
    """调用接口并返回延迟（秒）"""
    payload = {
        "messages": [{"role": "user", "content": query}],
        "edition": "lite",
        "search_source": "baidu_search_v2",
        "resource_type_filter": [
            {"type": "web", "top_k": 8},
            {"type": "video", "top_k": 0},
            {"type": "image", "top_k": 0},
            {"type": "aladdin", "top_k": 0},
        ],
    }

    start_time = time.time()
    response = requests.post(
        URL,
        headers=HEADERS,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=60
    )
    end_time = time.time()

    latency = end_time - start_time
    response.encoding = "utf-8"
    refs = json.loads(response.text)["references"]
    
    filtered = [
        {
            "title": r.get("title"),
            "content": r.get("content"),
            "date": r.get("date"),
            "rerank_score": r.get("rerank_score"),
            "authority_score": r.get("authority_score"),
        }
        for r in refs
    ]
    logging.info(
        json.dumps(
            {
                "query": query,
                "latency_sec": round(latency, 3),
                "status_code": response.status_code,
                "response": filtered,
            },
            ensure_ascii=False,
            indent=2   # 👈 关键：添加缩进
        )
    )

    return latency


def main():
    latencies = []

    logging.info("===== 开始 Web Search 测试 =====")

    for item in TEST_QUERIES:
        qtype = item["type"]
        query = item["query"]

        print(f"测试 [{qtype}]：{query}")
        latency = call_web_search(query)
        latencies.append(latency)

        print(f"  延迟：{latency:.3f} 秒")
        time.sleep(1.0)

    avg_latency = sum(latencies) / len(latencies)

    logging.info(f"===== 测试完成，平均延迟：{avg_latency:.3f} 秒 =====")

    print("\n====== 测试结果 ======")
    print(f"测试次数：{len(latencies)}")
    print(f"平均延迟：{avg_latency:.3f} 秒")
    print(f"日志文件：{log_filename}")


if __name__ == "__main__":
    main()
