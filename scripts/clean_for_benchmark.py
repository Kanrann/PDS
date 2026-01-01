import os
#清理问答对的历史数据，方便比对新版本性能
# ================= 你的路径配置 =================
WORK_DIR = r""

# 需要清理的文件列表
# 一定要确认文件名与你主脚本里的一致
FILES_TO_CLEAN = [
    "sensor_physics_sft.jsonl",  # 生成的结果文件
    "generation.log"             # 记录进度的日志文件
]

def clean_files():
    print(f"🧹 正在准备重置环境，目标目录: {WORK_DIR}")
    print("-" * 40)
    
    deleted_count = 0
    for filename in FILES_TO_CLEAN:
        file_path = os.path.join(WORK_DIR, filename)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ 已删除: {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除失败 {filename}: {e}")
        else:
            print(f"⚪️ 文件不存在 (无需清理): {filename}")

    print("-" * 40)
    if deleted_count > 0:
        print("🎉 环境已重置！现在运行主脚本将从【第 1 条数据】开始。")
    else:
        print("环境已经是干净的，可以直接开始测试。")

if __name__ == "__main__":
    # 为了防止误删，加一个简单的确认
    confirm = input("⚠️  确定要删除所有历史生成数据，重新开始吗？(y/n): ")
    if confirm.lower() == 'y':
        clean_files()
    else:
        print("已取消操作。")