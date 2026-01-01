import requests
import os
import zipfile
#从mineru获得处理结果
# ================= 配置区 =================
token = ""
batch_id_file = ""

# 这里填入你想保存的新位置（例如在你的 myprojects 下建立一个 results 文件夹）
NEW_BASE_DIR = ""
# ==========================================

header = {
    "Authorization": f"Bearer {token.strip()}"
}

def download_to_new_location():
    # 创建主结果目录
    if not os.path.exists(NEW_BASE_DIR):
        os.makedirs(NEW_BASE_DIR)
        print(f"创建根目录: {NEW_BASE_DIR}")

    with open(batch_id_file, 'r') as f:
        batch_ids = [line.strip() for line in f if line.strip()]

    for b_id in batch_ids:
        print(f"\n🚀 正在拉取批次数据: {b_id}")
        url = f"https://mineru.net/api/v4/extract-results/batch/{b_id}"
        
        try:
            res = requests.get(url, headers=header)
            if res.status_code == 200:
                results = res.json().get("data", {}).get("extract_result", [])
                
                for item in results:
                    if item.get("state") == "done":
                        zip_url = item.get("full_zip_url")
                        data_id = item.get("data_id") # 例如: .../batch_12/abc.pdf
                        
                        # --- 路径重定向逻辑 ---
                        # 获取 batch_x 这一层文件夹的名字
                        path_parts = data_id.split('/')
                        batch_folder_name = path_parts[-2] if len(path_parts) > 1 else "default_batch"
                        file_base_name = os.path.basename(data_id).replace(".pdf", "")
                        
                        new_batch_path = os.path.join(NEW_BASE_DIR, batch_folder_name)
                        extract_to = os.path.join(new_batch_path, f"{file_base_name}_result")
                        
                        os.makedirs(extract_to, exist_ok=True)
                        
                        # 下载并解压
                        print(f"  📥 下载并保存至 {batch_folder_name}: {file_base_name}")
                        zip_res = requests.get(zip_url)
                        
                        # 内存中直接解压或使用临时文件
                        temp_zip = os.path.join(NEW_BASE_DIR, "temp_download.zip")
                        with open(temp_zip, 'wb') as f_zip:
                            f_zip.write(zip_res.content)
                        
                        with zipfile.ZipFile(temp_zip, 'r') as z:
                            z.extractall(extract_to)
                        
                        os.remove(temp_zip)
            else:
                print(f"  ❌ 批次 {b_id} 请求失败")
        except Exception as e:
            print(f"  💥 处理出错: {e}")

if __name__ == "__main__":
    download_to_new_location()