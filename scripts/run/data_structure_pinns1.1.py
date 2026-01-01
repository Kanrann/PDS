import json
import os
import time
import logging
import re
import asyncio
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm

# ================= 配置区域 =================
API_KEY = ""  #填入 Key
BASE_URL = "https://api.siliconflow.cn/v1"#硅基流动平台，可以自行修改
MODEL_NAME = "deepseek-ai/DeepSeek-V3.2"  #推荐

# 并发数
CONCURRENCY = 15 
#请根据情况修改
WORK_DIR = r""
INPUT_FILE = os.path.join(WORK_DIR, "domain_chunks.jsonl")
OUTPUT_FILE = os.path.join(WORK_DIR, "sensor_physics_sft.jsonl")
LOG_FILE = os.path.join(WORK_DIR, "generation.log")

# ================= Prompt =================
#请根据你的任务灵活修改，这个框架很优秀建议沿用
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

# ================= 工具函数 =================
def setup_logger(log_file_path):
    logger = logging.getLogger("AsyncQA")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        # mode='w' 确保每次运行先清空日志文件
        fh = logging.FileHandler(log_file_path, mode='w', encoding='utf-8') 
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

# ================= 异步核心逻辑 =================

async def process_single_chunk(sem, client, text_chunk, chunk_id, logger):
    async with sem:  # 限制并发数
        retries = 3
        for attempt in range(retries):
            try:
                response = await client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"请阅读以下科学文献片段，并生成0-2个包含物理约束的问答对：\n\n{text_chunk}"}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                raw_content = response.choices[0].message.content
                cleaned_content = fix_json_string(raw_content)
                qa_data = json.loads(cleaned_content)
                
                return chunk_id, text_chunk, qa_data
                
            except json.JSONDecodeError:
                if attempt == retries - 1:
                    logger.error(f"Chunk {chunk_id}: JSON最终解析失败。Raw: {raw_content[:50]}...")
            except Exception as e:
                if "429" in str(e):
                    logger.warning(f"Chunk {chunk_id}: 触发限流 (429)，休眠 5秒...")
                    await asyncio.sleep(5)
                else:
                    logger.error(f"Chunk {chunk_id}: API 错误: {e}")
            
            if attempt < retries - 1:
                await asyncio.sleep(1 + attempt)
                
        return chunk_id, text_chunk, None

async def main():
    logger = setup_logger(LOG_FILE)
    logger.info(">>> 异步任务开始 <<<")
    
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    total_lines = count_lines(INPUT_FILE)
    if os.path.exists(OUTPUT_FILE):
        processed_count = count_lines(OUTPUT_FILE)
    else:
        processed_count = 0
        
    print(f"输入文件: {total_lines} 行")
    print(f"已处理: {processed_count} 行 (跳过)")
    
    lines_to_process = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < processed_count:
                continue
            if line.strip():
                lines_to_process.append((i+1, line.strip()))

    if not lines_to_process:
        print("所有数据已处理完毕。")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = []

    print(f"准备处理 {len(lines_to_process)} 条数据，并发数: {CONCURRENCY}")
    
    for idx, line in lines_to_process:
        try:
            data = json.loads(line)
            text = data.get('text', data.get('content', ''))
            c_id = data.get('id', f"line_{idx}")
            
            if len(text) < 100:
                continue
                
            task = process_single_chunk(sem, client, text, c_id, logger)
            tasks.append(task)
        except json.JSONDecodeError:
            pass
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
        pbar = tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="🚀 高速生成中")
        
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
                            logger.info(f"Chunk {chunk_id}: 成功生成 {valid_count} 条。")
                    else:
                        pass
                        
            except Exception as e:
                logger.error(f"主循环写入错误: {e}")

    logger.info(">>> 任务完成 <<<")
    print(f"\n处理完成！文件已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n任务被用户强制停止。")