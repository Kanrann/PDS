import os
import json
import re
#清洗从mineru得到的返回结果
# ================= 配置区 =================
BASE_DIR = ""
OUTPUT_FILE = ""
#这里根据你的结果分为多少份自主调整
BATCH_RANGE = range(1, 30)  # 处理 batch_1 到 batch_29
MIN_LENGTH = 300  # 过滤掉内容过短（少于300字）的文档

def clean_paper_content(text):
    """
    针对专业论文 Markdown 的清洗逻辑
    """
    # 1. 自动截断参考文献 (References)
    # 匹配常见的参考文献标题，截断其之后的所有内容
    ref_keywords = [r'\n#+ \s*References', r'\n#+ \s*参考文献', r'\n#+ \s*Bibliography']
    for kw in ref_keywords:
        parts = re.split(kw, text, flags=re.IGNORECASE)
        if len(parts) > 1:
            text = parts[0]
            break

    # 2. 移除图片引用 (MinerU 提取的格式通常是 ![](...))
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # 3. 移除超链接，但保留文字
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # 4. 移除多余的换行，保持段落整洁
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def build_dataset():
    extracted_count = 0
    skipped_count = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for i in BATCH_RANGE:
            batch_path = os.path.join(BASE_DIR, f"batch_{i}")
            if not os.path.exists(batch_path):
                print(f"跳过不存在的目录: {batch_path}")
                continue
            
            print(f"正在扫描: batch_{i}...")
            
            # 遍历每个以论文命名的文件夹
            for paper_folder in os.listdir(batch_path):
                folder_path = os.path.join(batch_path, paper_folder)
                if not os.path.isdir(folder_path):
                    continue
                
                # 寻找 Markdown 文件
                md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
                if not md_files:
                    skipped_count += 1
                    continue
                
                md_path = os.path.join(folder_path, md_files[0])
                
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # 执行清洗
                    cleaned_content = clean_paper_content(raw_content)
                    
                    # 质量检查
                    if len(cleaned_content) < MIN_LENGTH:
                        skipped_count += 1
                        continue
                    
                    # 构造基础 JSONL 条目
                    # 这里先用最通用的格式，方便后续改造成 QA 格式
                    data_item = {
                        "source": f"batch_{i}/{paper_folder}",
                        "title": paper_folder.replace('_', ' '),
                        "content": cleaned_content,
                        "metadata": {
                            "batch": i,
                            "char_count": len(cleaned_content)
                        }
                    }
                    
                    outfile.write(json.dumps(data_item, ensure_ascii=False) + '\n')
                    extracted_count += 1
                    
                except Exception as e:
                    print(f"处理 {md_path} 失败: {e}")

    print(f"\n处理完成！")
    print(f"成功提取: {extracted_count} 篇论文")
    print(f"跳过/无效: {skipped_count} 篇")
    print(f"结果已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dataset()