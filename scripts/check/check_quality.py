import json

FILE_PATH = ""

def check_physics_quality():
    total = 0
    has_formula = 0
    has_logic_words = 0
    
    # 物理逻辑关键词
    logic_keywords = [
    # 英文学术逻辑
    "physically", "mathematically", "arises from", "attributed to", 
    "consequences", "implies", "indicates", "demonstrates",
    "due to", "result of", "governed by", "leads to",
    "1)", "2)", "3)", 
    
    # 中文学术逻辑
    "归因于", "源于", "意味着", "表明", "推导", "机制", 
    "首先", "其次", "取决于", "表现为"
]
    
    print(f"正在检查: {FILE_PATH} ...")
    
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            total += 1
            data = json.loads(line)
            content = data['output']
            
            # 检查是否包含 LaTeX 公式
            if "$" in content or "\\" in content:
                has_formula += 1
                
            # 检查是否包含推理逻辑词
            if any(kw in content for kw in logic_keywords):
                has_logic_words += 1

    if total == 0:
        print("⚠️ 文件为空，还没有生成任何数据。")
        return

    print(f"📊 质量分析报告 (共 {total} 条数据):")
    print(f"--------------------------------------")
    print(f"🧮 含公式比例: {has_formula/total*100:.1f}%  (建议 >30%)")
    print(f"🧠 含逻辑比例: {has_logic_words/total*100:.1f}%  (建议 >80%)")
    print(f"--------------------------------------")
    
    if has_formula/total < 0.2:
        print("💡 建议：你的 System Prompt 可能需要强制模型多输出公式。")
    else:
        print("✅ 物理约束构建看起来很不错！")

if __name__ == "__main__":
    check_physics_quality()