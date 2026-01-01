import json
import os
import time
import logging
import re
import asyncio
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm

# ================= 1. ⚡️ 极速配置区域 =================
API_KEY = ""  # <--- 【必填】
BASE_URL = ""    #api调用平台链接
MODEL_NAME = ""  #选择你的模型

#以下建议根据sweet结果设置
# 【配置 1】并发数： 50
CONCURRENCY = 50

# 【配置 2】输入限制：放宽下限，提升上限。
MIN_TEXT_LENGTH = 100
MAX_TEXT_LENGTH = 3500 

# 【配置 3】超时斩杀：微调至 60秒
TIMEOUT_SECONDS = 60.0 

# 【配置 4】最大生成长度
MAX_OUTPUT_TOKENS = 1280

# 路径以及命名请合理修改
WORK_DIR = r""
INPUT_FILE = os.path.join(WORK_DIR, "domain_chunks.jsonl")
OUTPUT_FILE = os.path.join(WORK_DIR, "sensor_physics_sft.jsonl")
LOG_FILE = os.path.join(WORK_DIR, "generation.log")

# ================= 2. Prompt  =================
#请合理修改
SYSTEM_PROMPT = r"""你是一位传感器材料与器件物理领域的专家。
请分析用户提供的文献片段，提取用于微调大模型的问答对。

【核心目标：物理机理与数学表达并重】
1. **必须包含思维链 (CoT)**：
   - Output 必须展示“微观结构 -> 物理参数 -> 宏观性能”的推导逻辑。
   - 必须使用逻辑连接词（如：归因于、导致、遵循...定律、因此）。

2. **🚀 强制数学化约束 (关键)**：
   - 凡是涉及物理量（如灵敏度、电导率、活化能、势垒高度），**必须尽可能补充对应的数学表达**（使用 LaTeX 格式）。
   - **如果原文没有公式，请根据物理常识补全基础公式**。
   - 传感器领域常用公式示例：
     * 灵敏度：$S = R_a / R_g$ 或 $S = \Delta R / R_0$
     * 响应/恢复时间：$\tau_{res}$ (达到 90% 变化所需时间)
     * 活化能：Arrhenius 方程 $k = A e^{-E_a/RT}$
     * 吸附模型：Langmuir 等温线 $\theta = \frac{KP}{1+KP}$
     * 电阻变化：$R \propto e^{qV_b/kT}$

3. **LaTeX 格式要求**：
   - JSON字符串中的反斜杠必须转义。例如使用 \\alpha 表示 \alpha。

4. **格式与数量**：
   - 输出标准 JSON。
   - 根据质量生成 0-2 个问答对。无实质内容返回空列表。

输出示例：
{
  "qa_pairs": [
    {
      "instruction": "分析该材料气敏性能提升的原因。",
      "output": "性能提升主要归因于异质结的形成。根据耗尽层理论，异质结界面处形成了内建电场..."
    }
  ]
}
"""

# ================= 3. 工具函数 =================
def setup_logger(log_file_path):
    logger = logging.getLogger("AsyncQA")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_file_path, mode='a', encoding='utf-8') 
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
    return logger

def fix_json_string(json_str):
    json_str = json_str.replace("```json", "").replace("```", "").strip()
    try:
        json_str = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)
    except Exception:
        pass
    return json_str

def count_lines(filename):
    if not os.path.exists(filename): return 0
    with open(filename, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

# ================= 4. 核心逻辑 (斩杀版) =================
async def process_single_chunk(sem, client, text_chunk, chunk_id, logger):
    
    # 过滤器：只处理长度适中的文本
    if len(text_chunk) > MAX_TEXT_LENGTH:
        return chunk_id, text_chunk, None # 太长不读
    
    async with sem:
        # 极速版不重试：失败了就直接丢弃，不浪费时间重试
        retries = 1 
        
        for attempt in range(retries):
            try:
                # 🔪 斩杀逻辑：asyncio.wait_for 强制超时
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"请阅读以下科学文献片段，并生成0-2个包含物理约束的问答对：\n\n{text_chunk}"}
                        ],
                        temperature=0.3,
                        max_tokens=MAX_OUTPUT_TOKENS, # 限制废话
                        response_format={"type": "json_object"}
                    ),
                    timeout=TIMEOUT_SECONDS # 超过直接杀
                )
                
                raw_content = response.choices[0].message.content
                cleaned_content = fix_json_string(raw_content)
                qa_data = json.loads(cleaned_content)
                return chunk_id, text_chunk, qa_data

            except asyncio.TimeoutError:
                # 记录一下被杀掉的任务（可选）
                # logger.warning(f"Chunk {chunk_id}: 🔪 超时斩杀 ")
                return chunk_id, text_chunk, None
                
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    logger.warning(f"Chunk {chunk_id}: 限流 429，避让 5秒...")
                    await asyncio.sleep(5)
                else:
                    # 其他错误直接忽略，不记录Error以免刷屏
                    pass
                
        return chunk_id, text_chunk, None

# ================= 5. 主程序 =================
async def main():
    logger = setup_logger(LOG_FILE)
    print(f"=== ⚡️ 极速斩杀版启动 (并发: {CONCURRENCY}) ===")
    print(f"策略: 只读 {MIN_TEXT_LENGTH}-{MAX_TEXT_LENGTH}字 | 超时 {TIMEOUT_SECONDS}s 即杀 | 输出限 {MAX_OUTPUT_TOKENS} tokens")
    
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    # 进度检查
    total_lines = count_lines(INPUT_FILE)
    processed_count = 0
    if os.path.exists(OUTPUT_FILE):
        processed_count = count_lines(OUTPUT_FILE)
        
    print(f"总行数: {total_lines} | 已存盘: {processed_count}")
    
    # 快速加载数据
    print("正在加载数据队列...")
    lines_to_process = []
    skipped = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < processed_count: continue
            
            # 简单过滤，加速加载
            if len(line) < MIN_TEXT_LENGTH: 
                skipped += 1
                continue
                
            try:
                data = json.loads(line)
                text = data.get('text', data.get('content', ''))
                
                # 严格的长度过滤
                if len(text) < MIN_TEXT_LENGTH or len(text) > MAX_TEXT_LENGTH:
                    skipped += 1
                    continue
                    
                c_id = data.get('id', f"line_{i+1}")
                lines_to_process.append((c_id, text))
            except:
                pass

    print(f"有效任务: {len(lines_to_process)} 条 (已过滤不合格: {skipped} 条)")
    
    if not lines_to_process:
        print("无任务。")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = []

    for c_id, text in lines_to_process:
        tasks.append(process_single_chunk(sem, client, text, c_id, logger))
    
    # 执行
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
        pbar = tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="⚡️ Speed Run", unit="chk")
        
        valid_total = 0
        for future in pbar:
            try:
                chunk_id, origin_text, result = await future
                
                if result:
                    final_qas = result.get('qa_pairs', result) if isinstance(result, dict) else result
                    
                    if isinstance(final_qas, list) and len(final_qas) > 0:
                        valid_count = 0
                        for qa in final_qas:
                            q = qa.get("instruction", qa.get("question"))
                            a = qa.get("output", qa.get("answer"))
                            
                            if q and a:
                                record = {
                                    "source_chunk_id": chunk_id,
                                    "instruction": q,
                                    "output": a,
                                    "context_preview": origin_text[:50]
                                }
                                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                                valid_count += 1
                        
                        if valid_count > 0:
                            f_out.flush()
                            valid_total += valid_count
                            logger.info(f"Chunk {chunk_id}: +{valid_count}")
                            pbar.set_postfix({"✅ Saved": valid_total})
            except Exception:
                pass # 极速模式下忽略写入错误，保持奔跑

    print(f"\n=== 完成 ===")
    print(f"新增数据: {valid_total} 条")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 用户强制停止")