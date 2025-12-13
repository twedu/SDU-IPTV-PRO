import requests
import os
import re
import hashlib

# --- 配置 ---
SOURCE_URL = "https://raw.githubusercontent.com/plsy1/iptv/refs/heads/main/unicast/unicast-ku9.m3u"
OUTPUT_PATH = "temp/temp-unicast.m3u"
# 哈希文件路径，用于记录上次的源文件哈希
HASH_FILE_PATH = ".data/unicast.hash"

# --- 核心功能 ---
def ensure_dir_exists(filepath):
    """确保文件所在的目录存在"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def download_file(url):
    """下载文件并返回内容"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"下载文件失败: {e}")
        return None

def get_file_hash(content):
    """计算文件内容的MD5哈希"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_last_hash():
    """从文件加载上次的哈希值"""
    if os.path.exists(HASH_FILE_PATH):
        with open(HASH_FILE_PATH, 'r') as f:
            return f.read().strip()
    return None

def save_current_hash(hash_value):
    """保存当前的哈希值到文件"""
    ensure_dir_exists(HASH_FILE_PATH)
    with open(HASH_FILE_PATH, 'w') as f:
        f.write(hash_value)

def parse_m3u(content):
    """解析M3U内容，返回频道列表"""
    lines = content.splitlines()
    extm3u_line = lines[0] if lines and lines[0].startswith('#EXTM3U') else '#EXTM3U'
    channels = []
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            match = re.search(r'tvg-name="([^"]*)".*group-title="([^"]*)".*tvg-logo="([^"]*)",(.*)', line)
            if match:
                name, group, logo, url = match.groups()
                channels.append({'name': name, 'group': group, 'logo': logo, 'url': url})
                i += 1
            else:
                i += 1
        else:
            i += 1
    return extm3u_line, channels

def process_channels(channels):
    """处理频道：排序、分组、移动等"""
    # 预定义分组
    central_channels = ['CCTV1', 'CCTV2', 'CCTV3', 'CCTV4', 'CCTV5', 'CCTV5+', 'CCTV6', 'CCTV7', 'CCTV8', 'CCTV9', 'CCTV10', 'CCTV11', 'CCTV12', 'CCTV13', 'CCTV14', 'CCTV15', 'CCTV16', 'CCTV17']
    shandong_channels = ['山东卫视', '齐鲁频道', '山东文旅', '山东综艺', '山东生活', '山东农科', '山东新闻', '山东少儿', '山东教育', '山东体育']
    
    # 分组
    def get_group(channel):
        if channel['name'] in central_channels:
            return '央视频道'
        elif channel['name'] in shandong_channels:
            return '山东频道'
        elif '广播' in channel['name']:
            return '广播频道'
        elif 'CGTN' in channel['name']:
            return '其他频道'
        return channel['group'] or '其他频道'

    for ch in channels:
        ch['group'] = get_group(ch)

    # 排序
    def sort_key(channel):
        if channel['name'] == 'CCTV1':
            return (0, channel['name'])
        if channel['name'] == '山东卫视':
            return (1, channel['name'])
        if channel['group'] == '央视频道':
            return (2, channel['name'])
        if channel['group'] == '山东频道':
            return (3, channel['name'])
        if channel['group'] == '广播频道':
            return (4, channel['name'])
        return (5, channel['name'])
    
    channels.sort(key=sort_key)

    # 移动频道
    def move_channel(ch_list, name, after_name, new_group=None):
        src_idx = next((i for i, ch in enumerate(ch_list) if ch['name'] == name), None)
        if src_idx is not None:
            channel = ch_list.pop(src_idx)
            if new_group:
                channel['group'] = new_group
            dst_idx = next((i for i, ch in enumerate(ch_list) if ch['name'] == after_name), None)
            if dst_idx is not None:
                ch_list.insert(dst_idx + 1, channel)
                print(f"已将 {name} 移动到 {after_name} 后面 (位置: {dst_idx + 1})")
            else:
                ch_list.append(channel)
                print(f"未找到目标频道 {after_name}，已将 {name} 移动到列表末尾")
        else:
            print(f"未找到源频道 {name}")

    # 执行特定移动
    move_channel(channels, 'CCTV4欧洲', '山东少儿')
    move_channel(channels, 'CCTV4美洲', '山东少儿')
    move_channel(channels, '山东经济广播', '', '广播频道')

    return channels

def save_m3u(extm3u_line, channels, output_path):
    """保存频道列表到M3U文件"""
    ensure_dir_exists(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(extm3u_line + '\n')
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="{ch["group"]}" tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')

# --- 主程序 ---
if __name__ == "__main__":
    print("处理单播源...")
    
    # 1. 读取上次的哈希
    last_hash = load_last_hash()
    
    # 2. 下载源文件
    source_content = download_file(SOURCE_URL)
    if not source_content:
        print("由于下载失败，停止处理。")
        exit(1)
        
    # 3. 计算当前哈希
    current_hash = get_file_hash(source_content)
    
    # 4. 比较哈希
    if current_hash == last_hash:
        print("源文件未发生变化，跳过处理。")
    else:
        print(f"源文件发生变化: 旧哈希 {last_hash[:8] if last_hash else 'N/A'}... -> 新哈希 {current_hash[:8]}...")
        
        # --- 原始处理逻辑 ---
        extm3u_line, channels = parse_m3u(source_content)
        print(f"解析完成，共 {len(channels)} 个频道")
        
        print("开始处理频道排序和分类...")
        processed_channels = process_channels(channels)
        print("频道处理完成")
        
        save_m3u(extm3u_line, processed_channels, OUTPUT_PATH)
        print(f"处理完成，已保存到 {OUTPUT_PATH}")

    # 5. 【关键】无论是否变化，都更新哈希文件，为下次运行做准备
    save_current_hash(current_hash)
