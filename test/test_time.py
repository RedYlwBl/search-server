import requests
import datetime

def get_shanghai_time() -> datetime.datetime:
    """访问 worldtimeapi 获取上海实时时间，返回 datetime 对象"""
    url = "https://worldtimeapi.org/api/timezone/Asia/Shanghai"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()          # 网络错误直接抛异常
    data = resp.json()
    # datetime_string 格式：2025-12-24T16:08:45.123456+08:00
    return datetime.datetime.fromisoformat(data["datetime"])

if __name__ == "__main__":
    sh_time = get_shanghai_time()
    print("上海现在时间：", sh_time)
    print("时间戳：", sh_time.timestamp())