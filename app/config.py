# app/config.py
# app/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# 自动计算项目的根目录绝对路径（也就是 app 文件夹的上一级）
# __file__ 是当前 config.py 的路径，dirname 向上推一层是 app，再推一层是根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    # 声明我们需要一个叫 DATABASE_URL 的环境变量
    database_url: str
    DEEPSEEK_API_KEY: str = ""
    # 明确告诉 Pydantic 这个 .env 文件的绝对路径在哪里
    model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding="utf-8")

# 实例化配置对象
settings = Settings()