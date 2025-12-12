import os
import filecmp

# --- 配置 ---
# 定义文件路径
temp_unicast_path = 'temp/temp-unicast.m3u'
temp_multicast_r2h_path = 'temp/temp-multicast-r2h.m3u'
temp_multicast_nofcc_path = 'temp/temp-multicast-nofcc.m3u'
custom_path = 'custom/custom.m3u'

# 定义最终输出文件路径
final_unicast_path = 'unicast.m3u'
final_multicast_r2h_path = 'multicast-r2h.m3u'
final_multicast_nofcc_path = 'multicast-nofcc.m3u'

# 标记，用于记录是否有文件被实际更新
any_file_updated = False

# --- 核心合并函数 ---
def merge_files(temp_path, custom_path, final_path):
    """
    合并临时文件和自定义文件，并仅在内容有变化时更新最终文件。
    """
    global any_file_updated
    temp_content = ""
    custom_content = ""
    
    # 读取临时文件内容
    if os.path.exists(temp_path):
        with open(temp_path, 'r', encoding='utf-8') as f:
            temp_content = f.read()
            
    # 读取自定义文件内容
    if os.path.exists(custom_path):
        with open(custom_path, 'r', encoding='utf-8') as f:
            custom_content = f.read()

    # 合并内容
    merged_content = temp_content + '\n' + custom_content

    # 检查最终文件是否已存在
    if os.path.exists(final_path):
        # 创建一个临时文件来存放新的合并内容，用于比较
        temp_merged_path = final_path + '.tmp'
        with open(temp_merged_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
            
        # 比较新旧文件内容是否一致
        if not filecmp.cmp(final_path, temp_merged_path, shallow=False):
            # 内容不一致，更新文件
            os.replace(temp_merged_path, final_path)
            print(f"成功合并: {temp_path} + {custom_path} -> {final_path} (内容已更新)")
            any_file_updated = True
        else:
            # 内容一致，不更新，删除临时文件
            os.remove(temp_merged_path)
            print(f"无变化: {final_path} 内容已是最新，跳过更新。")
    else:
        # 文件不存在，直接创建
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        print(f"成功创建: {temp_path} + {custom_path} -> {final_path} (新文件)")
        any_file_updated = True

# --- 主程序 ---
if __name__ == "__main__":
    print("开始合并播放列表...")
    
    # 执行合并
    merge_files(temp_unicast_path, custom_path, final_unicast_path)
    merge_files(temp_multicast_r2h_path, custom_path, final_multicast_r2h_path)
    merge_files(temp_multicast_nofcc_path, custom_path, final_multicast_nofcc_path)
    
    # 输出最终状态
    if any_file_updated:
        print("合并完成，检测到文件更新。")
    else:
        print("合并完成，所有文件均无变化。")
