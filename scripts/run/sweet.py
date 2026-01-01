import json
import os
import statistics
import re

# ================= 配置 =================
# 你的结果文件路径
FILE_PATH = r""

# 你当前设置的生成限制 (用于计算截断风险)
CURRENT_MAX_TOKENS = 1024 
# 粗略换算：1 token ≈ 1.5 中文字符 (根据 DeepSeek tokenizer 估算)
TOKEN_CHAR_RATIO = 1.5 
WARNING_LENGTH = CURRENT_MAX_TOKENS * TOKEN_CHAR_RATIO * 0.9 # 达到 90% 长度预警

def check_quality(text):
    """简单判断单条数据的含金量"""
    has_formula = 1 if ("$" in text or "\\" in text) else 0
    # 逻辑词库
    logic_words = ["归因于", "导致", "意味着", "表明", "推导", "遵循", "因此", "because", "due to"]
    has_logic = 1 if any(w in text for w in logic_words) else 0
    return has_formula, has_logic

def analyze_output_sweet_spot():
    print(f"正在分析结果文件: {FILE_PATH} ...")
    
    if not os.path.exists(FILE_PATH):
        print("❌ 文件不存在，请先运行生成脚本。")
        return

    instruction_lens = [] # 问题长度
    output_lens = []      # 答案长度
    high_quality_indices = [] # 高质量答案的索引
    truncated_suspects = 0    # 疑似被截断的数量

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip(): continue
            try:
                data = json.loads(line)
                inst = data.get('instruction', data.get('question', ''))
                out = data.get('output', data.get('answer', ''))
                
                i_len = len(inst)
                o_len = len(out)
                
                instruction_lens.append(i_len)
                output_lens.append(o_len)
                
                # 质量检测
                f_score, l_score = check_quality(out)
                if f_score and l_score:
                    high_quality_indices.append(i)
                
                # 截断检测：如果答案长度非常接近最大 Token 限制，且不以标点结束
                if o_len > WARNING_LENGTH:
                    # 简单检查末尾标点
                    if out.strip()[-1] not in ['。', '.', '!', '}', ']']:
                        truncated_suspects += 1
                        
            except:
                pass

    total = len(output_lens)
    if total == 0:
        print("⚠️ 结果文件为空。")
        return

    # 统计数据
    avg_out = statistics.mean(output_lens)
    med_out = statistics.median(output_lens)
    max_out = max(output_lens)
    
    hq_count = len(high_quality_indices)
    hq_rate = (hq_count / total) * 100

    print(f"\n📈 === 结果分布报告 (基数: {total} 条) ===")
    print(f"✅ 有效产出: {total} 条")
    print(f"💎 高质量率: {hq_rate:.1f}% (同时包含公式+逻辑词)")
    print(f"✂️ 疑似截断: {truncated_suspects} 条 (占比 {truncated_suspects/total*100:.1f}%)")
    print("-" * 30)
    
    print(f"📝 **Output (回答) 长度统计**:")
    print(f"   - 平均: {int(avg_out)} 字")
    print(f"   - 中位: {int(med_out)} 字")
    print(f"   - 最长: {max_out} 字")
    
    # 长度分布直方图
    print(f"\n📊 **回答长度分布 (寻找 MAX_OUTPUT_TOKENS 甜蜜点)**:")
    bins = [0, 200, 500, 800, 1200, 2000, 5000]
    for k in range(len(bins)-1):
        low, high = bins[k], bins[k+1]
        count = sum(1 for l in output_lens if low <= l < high)
        bar = "█" * int(count / total * 20)
        print(f"   [{low:4d}-{high:<4d} 字]: {count:4d} | {bar} ({count/total*100:.1f}%)")

    print("-" * 30)
    
    # 建议部分
    print("💡 **参数调整建议 (Sweet Spot)**:")
    
    # 1. 关于 MAX_OUTPUT_TOKENS
    if truncated_suspects > total * 0.05:
        print(f"   🔴 **警告**: 有 >5% 的回答可能被截断了！建议调大 `MAX_OUTPUT_TOKENS`。")
        print(f"      推荐值: {int(max_out / 1.2)} tokens (或更大)")
    elif max_out < WARNING_LENGTH * 0.5:
        print(f"   🟢 **空间**: 模型回答都很精简。你可以调小 `MAX_OUTPUT_TOKENS` 以稍微提升并发速度。")
        print(f"      推荐值: {int(max_out / 1.3)} tokens")
    else:
        print(f"   🔵 **完美**: `MAX_OUTPUT_TOKENS` 设置得刚刚好，既没截断也没浪费。")

    # 2. 关于 MIN_TEXT_LENGTH (通过 output 反推)
    # 计算高质量回答对应的平均输入长度
    if hq_count > 0:
        hq_inst_lens = [instruction_lens[i] for i in high_quality_indices]
        avg_hq_inst = statistics.mean(hq_inst_lens)
        print(f"\n   🟡 **输入限制**: 高质量回答(含公式)通常来自长度约 {int(avg_hq_inst)} 字的问题。")
        print(f"      建议 `MIN_TEXT_LENGTH` 不要超过 {int(avg_hq_inst * 0.5)}，否则可能漏掉好问题。")

if __name__ == "__main__":
    analyze_output_sweet_spot()