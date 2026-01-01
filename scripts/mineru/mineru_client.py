import os
import requests
#用mineru处理文件
# --- 基础配置 ---
token = "" #mineru的api
apply_url = "https://mineru.net/api/v4/file-urls/batch"
input_dir = ""  # PDF 所在文件夹
batch_log_file = ""    # 用于存放生成的 batch_id，方便后续查询

# --- 准备工作：扫描本地 PDF 文件 ---
file_paths = []
for root, dirs, files in os.walk(input_dir):
    for f in files:
        if f.lower().endswith('.pdf'):
            file_paths.append(os.path.join(root, f))

# 官方限制单次申请不能超过 200 个
BATCH_LIMIT = 200

header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

for i in range(0, len(file_paths), BATCH_LIMIT):
    current_batch_files = file_paths[i : i + BATCH_LIMIT]
    
    # 构造符合官方格式的 data 数据体
    data = {
        "files": [
            {"name": os.path.basename(fp), "data_id": fp} 
            for fp in current_batch_files
        ],
        "model_version": "vlm"
    }

    try:
        # 1.申请上传链接 (POST)
        response = requests.post(apply_url, headers=header, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print('response success. result:{}'.format(result))
            
            if result["code"] == 0:
                batch_id = result["data"]["batch_id"]
                urls = result["data"]["file_urls"]
                
                # --- 关键步骤：保存 batch_id ---
                with open(batch_log_file, 'a') as log:
                    log.write(f"{batch_id}\n")
                
                print(f'batch_id:{batch_id}, urls数量:{len(urls)}')
                
                # 2. 循环执行上传 (PUT)
                for j in range(0, len(urls)):
                    with open(current_batch_files[j], 'rb') as f:
                        # 上传文件时，无须设置 Content-Type 请求头
                        res_upload = requests.put(urls[j], data=f)
                        if res_upload.status_code == 200:
                            print(f"File {j+1}/{len(urls)}: {current_batch_files[j]} upload success")
                        else:
                            print(f"File {j+1}: upload failed, status: {res_upload.status_code}")
            else:
                # 官方代码中 result 是 dict，需使用 get 或 ["msg"]
                print('apply upload url failed, reason:{}'.format(result.get("msg", "unknown")))
        else:
            print('response not success. status:{} ,result:{}'.format(response.status_code, response.text))
            
    except Exception as err:
        print(f"An error occurred: {err}")

print(f"\n任务全部处理完成。所有的 batch_id 已记录在 {batch_log_file} 中。")