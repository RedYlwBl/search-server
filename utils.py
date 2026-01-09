"""
工具函数
"""

from typing import Any, Dict, List


def split_messages_by_role(
    messages: List[Dict[str, Any]],
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """划分消息类型"""
    system_contents = []
    history = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "system" and content:
            system_contents.append(content)
        elif role in ("user", "assistant"):
            history.append(msg)
        # tool / function 可在这里扩展

    if system_contents:
        system_msg = {
            "role": "system",
            "content": "\n\n".join(system_contents),
        }
    return system_msg, history


def msg_len(msg: Dict[str, Any]) -> int:
    return len(msg.get("content", ""))


def group_by_rounds(messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    rounds = []
    current = []

    for msg in messages:
        if msg["role"] == "user":
            if current:
                rounds.append(current)
                current = []
        current.append(msg)

    if current:
        rounds.append(current)

    return rounds


def truncate_by_rounds_and_chars(
    messages: List[Dict[str, Any]],
    max_rounds: int = 5,
    max_chars: int = 8000,
    debug: bool = False,
) -> List[Dict[str, Any]]:
    """
    裁剪 user / assistant 历史：
    - 最近轮次优先
    - 整轮保留
    - 字数兜底
    """

    rounds = group_by_rounds(messages)

    # 只保留最近 N 轮
    rounds = rounds[-max_rounds:]
    kept: List[Dict[str, Any]] = []
    total_chars = 0

    # 从最新轮开始，向前“前插”
    for i, r in enumerate(reversed(rounds)):
        r_chars = sum(msg_len(m) for m in r)
        if total_chars + r_chars > max_chars:
            break

        kept = r + kept   # 前插，顺序天然正确
        total_chars += r_chars

    # 防御：确保以 user 开头
    if kept and kept[0]["role"] == "assistant":
        kept = kept[1:]

    return kept