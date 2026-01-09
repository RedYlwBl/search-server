
from pydantic import BaseModel
from typing import AsyncGenerator, List, Dict, Any, Union, Optional
from datetime import datetime

# -------------------- 请求/响应模型 --------------------
class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.3
    top_p: float = 0.95
    max_tokens: int = 3000
    stream: bool = False
    location: Optional[str] = None



# 语言匹配规则
LANGUAGE_MATCH_SYSTEM = {
    "role": "system",
    "content": (
        "【语言匹配规则（重要）】\n"
        "请根据用户问题的语言来回复：\n"
        "- 如果用户用中文提问，请用中文回复\n"
        "- 如果用户用英文提问，请用英文回复\n"
        "- 如果用户用其他语言提问，请用相同的语言回复\n"
        "始终与用户使用的语言保持一致。"
    ),
}

# 兜底提示词
FALLBACK_SYSTEM = {
    "role": "system",
    "content": (
        "当用户的输入，不完整、缺乏明确含义、仅是打招呼、"
        "或无法判断其真实意图时：\n"
        "1. 不要输出时间、日期或无关信息\n"
        "2. 使用简短、友好、自然的方式引导用户补充问题\n"
    ),
}

# 数据准确性和引用规则
DATA_ACCURACY_SYSTEM = {
    "role": "system",
    "content": (
        "【数据准确性和引用规则】\n"
        "1. 数据优先级：最近5轮对话内已通过 search 获取并确认的信息，优先于本轮重新搜索结果。\n"
        "2. 稳定性原则：近期对话中，除非必要，不得用新 search 的结果推翻最近5轮对话中确认的结果。\n"
        "3. 问题相关性：回答时仅引用与当前问题直接相关的信息，不添加无关内容。\n"
        "4. 时间系统： 若问题涉及【明天 / 后天 / 是否放假 / 节日 / 日期计算 / 倒计时】等，必须基于【今日基准时间】进行推理计算，禁止直接照抄。\n"
        " 仅当用户今日时间，星期，时间信息时，可以直接根据【今日基准时间】进行回复。"
    ),
}


# 今日基准时间
def get_datatime_now():
    now = datetime.now()
    TIME_SYSTEM = {
        "role": "system",
        "content": (
            "【今日基准时间】: 时间信息（服务器北京时间）,用于时间推理，不得机械复述。\n"
            f"今日日期：{now.strftime('%Y-%m-%d')}\n"
            f"星期：{now.strftime('%A')}\n"
            f"当前时间：{now.strftime('%H:%M:%S')}\n "
        ),
    }
    return TIME_SYSTEM


# 工具提示词
TOOL_RULE_SYSTEM = {
    "role": "system",
    "content": (
        "【工具使用规则（严格执行）】\n"
        "1. 只要问题涉及以下任一方面，必须调用工具 search，禁止凭记忆回答：\n"
        " - 涉及【当前 / 最新 / 现在 / 今日 / 现任 / 排名 / 收盘 / 股价 / 汇率 / 天气 / 新闻 / 事件 / 赛果 / 是否晋级 / 官方状态】等实时或近期事实。\n"
        " - 涉及【金融数据】（股价、指数、汇率、商品价格）\n"
        " - 涉及【政治人物、国家领导人、现任职位】的问题\n"
        " - 涉及【体育赛事结果、排名、是否晋级】的问题\n"
        " - 涉及【人物所属关系】的问题（如某球员效力于哪个球队、某人属于哪个组织）\n"
        " - 涉及【数量、统计、分布】的问题（如有多少个、多少家、多少座、多少种类、全国共有多少）\n"
        "2. 若上述信息已在最近 5 轮对话中通过 search 获得（需要严格匹配），且用户未要求更新，禁止重复调用 search。\n"
        "3. 询问【时间 / 日期 / 星期】时，直接根据系统时间进行计算，不得调用 search。\n"
        # "4. 当需要了解相关节假日，假期情况，可结合 search。\n"
    ),
}

# 工具描述
TOOLS_DESC = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "用于获取需要依赖外部事实的信息，适用于以下问题类型："
                "实时或近期事实（如当前状态、最新数据、排名、赛果、天气、新闻、事件）、"
                "金融市场相关数据（股价、指数、汇率、商品价格）、"
                "政治人物或国家领导人的现任职位信息、"
                "以及体育赛事结果或晋级情况、"
                "各种数量、统计、分布的问题。"
                "禁止依赖模型内部知识回答。但是最近5轮对话中已存在可用的 search 结果时（需要严格匹配），不得重复调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用于搜索的关键词或完整问题描述"},
                },
                "required": ["query"],
            },
        },
    }
]


# 明确“会随时间变化的主题”
DATE_SENSITIVE_TOPICS = [
    "天气", "新闻", "价格", "股价", "汇率",
    "油价", "黄金", "指数", "现任",
    "发布", "疫情", "比赛", "票房",
    "现在", "领导人", "首相", "总统"
]

# 明确“时间指示词”
TIME_WORDS = [
    # 今天
    "今天", "今日", "当日", "当天",
    # 昨天
    "昨天", "昨日",
    # 明天
    "明天", "明日",
    # 近期
    "最近", "近期", "近来", "这几天",
    # 周
    "本周", "这周", "上周", "下周",
    # 月
    "本月", "这个月", "上个月", "下个月",
    # 年
    "今年", "去年", "明年",
]


if __name__ == "__main__":
    print(get_datatime_now())