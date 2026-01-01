import os
import json

# ================= 路径配置 =================
# 切块方便使用
INPUT_FILE = ""
OUTPUT_FILE = ""

def chunk_text(text, chunk_size=1200, overlap=200):
    """
    将长文本切分为带重叠的片段
    chunk_size: 每个片段的字符数
    overlap: 相邻片段重叠的字符数，保证语义连贯
    """
    chunks = []
    start = 0
    if not text:
        return chunks
        
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        # 下一次开始的位置是 当前结束位置 减去 重叠部分
        start += (chunk_size - overlap)
        # 防止死循环
        if chunk_size <= overlap:
            break
    return chunks

def run_chunking():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误：找不到输入文件 {INPUT_FILE}")
        return

    print(f"🚀 开始处理文件: {INPUT_FILE}")
    chunk_count = 0
    paper_count = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        with open(INPUT_FILE, "r", encoding="utf-8") as f_in:
            for line in f_in:
                try:
                    data = json.loads(line)
                    content = data.get('content', '')
                    source = data.get('source', 'unknown')
                    
                    # 执行切片
                    chunks = chunk_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        chunk_item = {
                            "source": source,
                            "chunk_id": i,
                            "text": chunk.strip()
                        }
                        f_out.write(json.dumps(chunk_item, ensure_ascii=False) + '\n')
                        chunk_count += 1
                    
                    paper_count += 1
                except Exception as e:
                    print(f"⚠️ 处理某行时出错: {e}")

    print(f"✅ 处理完成！")
    print(f"统计：共处理 {paper_count} 篇论文，生成 {chunk_count} 个切片片段。")
    print(f"结果保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_chunking()