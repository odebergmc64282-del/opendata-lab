"""公共配置（本地开发用最小版本，最终以 C 维护的 config.py 为准）。

对应 《01_INTERFACE_CONTRACT.md》2.1 节：三个城市的编码、显示名、经纬度、预报时区。
清洗层只用 city_code 做合法性校验，不需要经纬度，但为了与契约完全一致这里一并保留。
"""

CITY_CONFIG: dict[str, dict] = {
    "guangzhou": {
        "name": "广州",
        "latitude": 23.1291,
        "longitude": 113.2644,
        "timezone": "Asia/Shanghai",
    },
    "beijing": {
        "name": "北京",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "timezone": "Asia/Shanghai",
    },
    "shanghai": {
        "name": "上海",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "timezone": "Asia/Shanghai",
    },
}
