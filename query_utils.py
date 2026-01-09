"""
查询优化工具函数
"""
import re
from datetime import datetime
from typing import Optional

from schema import DATE_SENSITIVE_TOPICS, TIME_WORDS


def today_str() -> str:
    """获取今天的日期字符串"""
    return datetime.now().strftime("%Y-%m-%d")


def should_append_date(query: str) -> bool:
    """
    仅当：
    - 问题涉及时间变化主题
    - 或明确包含时间指示词
    才追加日期
    """
    return (
        any(t in query for t in DATE_SENSITIVE_TOPICS)
        or any(w in query for w in TIME_WORDS)
    )


def is_weather_query(query: str) -> bool:
    """
    判断是否是天气相关的查询（使用关键词判断）
    """
    weather_keywords = ["天气", "气温", "温度", "下雨", "下雪", "晴天", "阴天", "多云", "降雨", "降雪", "台风", "暴雨"]
    return any(keyword in query for keyword in weather_keywords)


def build_search_query(user_query: str) -> str:
    """
    构建搜索查询（非流式使用，仅追加日期）
    """
    if should_append_date(user_query):
        return f"{user_query}，（今日日期：{today_str()}）"
    return user_query

def extract_province_city(location: str) -> str | None:
    """
    从地址中提取 '省/自治区/直辖市 + 市' 级别信息
    """
    if not location:
        return None

    province = None
    city = None

    # 1️⃣ 提取省 / 自治区 / 特别行政区
    province_pattern = (
        r'(北京市|天津市|上海市|重庆市|'
        r'[^省]+省|'
        r'[^自治区]+自治区|'
        r'香港特别行政区|澳门特别行政区)'
    )
    province_match = re.search(province_pattern, location)
    if province_match:
        province = province_match.group(1)

    # 2️⃣ 提取市
    city_match = re.search(r'([^省自治区]+市)', location)
    if city_match:
        city = city_match.group(1)

    # 3️⃣ 直辖市兜底（市 == 省）
    if province and province in ["北京市", "天津市", "上海市", "重庆市"]:
        return province

    if province and city:
        return f"{province}{city}"
    
    if province is None and city is None:
        return location
    return province or city





def optimize_search_query(query: str, location: Optional[str] = None) -> str:
    """
    优化搜索查询（流式使用）：
    1. 如果是天气查询且query中没有包含location，则添加location
    2. 如果需要，追加日期信息
    """
    # # 判断是否是天气查询
    # if is_weather_query(query) and location:
    #     if location not in query:
    #         query = f"{query} {location}"
    
    # 追加日期信息
    if should_append_date(query):
        return f"{query}，（今日日期：{today_str()}）"
    return query


if __name__ == "__main__":
    # 测试提取各个省/市/直辖市/特别行政区
    pass