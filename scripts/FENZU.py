import os
import shutil

def organize_pdfs(src_dir, dest_dir, batch_size=1000):
    # 1. 检查并创建目标根目录
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        print(f"创建目标目录: {dest_dir}")

    # 2. 获取源目录下所有 PDF 文件
    # 使用 listdir 并过滤，确保只处理 .pdf 文件
    all_files = [f for f in os.listdir(src_dir) 
                 if os.path.isfile(os.path.join(src_dir, f)) and f.lower().endswith('.pdf')]
    
    total_files = len(all_files)
    print(f"共检测到 {total_files} 个 PDF 文件。")

    # 3. 分组移动
    for i in range(0, total_files, batch_size):
        # 计算当前是第几组
        batch_num = (i // batch_size) + 1
        current_batch_folder = os.path.join(dest_dir, f"batch_{batch_num}")
        
        # 创建子文件夹
        if not os.path.exists(current_batch_folder):
            os.makedirs(current_batch_folder)
        
        # 获取当前这一组的文件切片
        batch_files = all_files[i : i + batch_size]
        
        for file_name in batch_files:
            src_file_path = os.path.join(src_dir, file_name)
            dest_file_path = os.path.join(current_batch_folder, file_name)
            
            try:
                shutil.move(src_file_path, dest_file_path)
            except Exception as e:
                print(f"错误: 无法移动文件 {file_name} -> {e}")

        print(f"已完成: {current_batch_folder} (存放 {len(batch_files)} 个文件)")

if __name__ == "__main__":
    #这些路径体积过大，你可以放在这个项目区之外
    #源文件目录
    SOURCE = ""
    #结果文件目录
    DEST = ""
    
    # 执行脚本，每组 1000 个
    organize_pdfs(SOURCE, DEST, batch_size=1000)
    print("\n所有文件已完成分箱！")