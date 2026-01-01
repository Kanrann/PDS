import os
from openai import OpenAI
#检查硅基流动可使用模型
API_KEY = os.getenv("SILICONFLOW_API_KEY", "你的api")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

try:
    print("正在连接 SiliconFlow 获取模型列表...")
    models = client.models.list()
    
    print("\n✅ 找到以下 DeepSeek 相关模型：")
    found = False
    for m in models.data:
        # 只打印名字里带 deepseek 的
        if "deepseek" in m.id.lower():
            print(f"  - {m.id}")
            found = True
            
    if not found:
        print("  (未找到包含 deepseek 名字的模型)")

    print("\n✅ 找到以下 Llama 3.2 相关模型：")
    for m in models.data:
        if "llama" in m.id.lower() and "3.2" in m.id:
            print(f"  - {m.id}")

except Exception as e:
    print(f"❌ 获取失败: {e}")