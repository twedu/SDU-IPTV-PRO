import requests
import os
import re
import hashlib

# --- 配置 ---
SOURCE_URL = "https://raw.githubusercontent.com/plsy1/iptv/refs/heads/main/multicast/multicast-weifang.m3u"
OUTPUT_PATH_R2H = "temp/temp-multicast-r2h.m3u"
OUTPUT_PATH_NOFCC = "temp/temp-multicast-nofcc.m3u"
# 哈希文件路径
HASH_FILE_PATH = ".data/multicast.hash"

# --- 核心功能 (复用 unicast 的) ---
def ensure_dir_exists(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def download_file(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"下载文件失败: {e}")
        return None

def get_file_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_last_hash():
    if os.path.exists(HASH_FILE_PATH):
        with open(HASH_FILE_PATH, 'r') as f:
            return f.read().strip()
    return None

def save_current_hash(hash_value):
    ensure_dir_exists(HASH_FILE_PATH)
    with open(HASH_FILE_PATH, 'w') as f:
        f.write(hash_value)

# --- 原始处理逻辑 ---
def parse_m3u(content):
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
    # (此处的逻辑与 unicast.py 完全相同，为简洁起见直接复制)
    central_channels = ['CCTV1', 'CCTV2', 'CCTV3', 'CCTV4', 'CCTV5', 'CCTV5+', 'CCTV6', 'CCTV7', 'CCTV8', 'CCTV9', 'CCTV10', 'CCTV11', 'CCTV12', 'CCTV13', 'CCTV14', 'CCTV15', 'CCTV16', 'CCTV17']
    shandong_channels = ['山东卫视', '齐鲁频道', '山东文旅', '山东综艺', '山东生活', '山东农科', '山东新闻', '山东少儿', '山东教育', '山东体育']
    
    def get_group(channel):
        if channel['name'] in central_channels: return '央视频道'
        if channel['name'] in shandong_channels: return '山东频道'
        if '广播' in channel['name']: return '广播频道'
        if 'CGTN' in channel['name']: return '其他频道'
        return channel['group'] or '其他频道'

    for ch in channels: ch['group'] = get_group(ch)

    def sort_key(channel):
        if channel['name'] == 'CCTV1': return (0, channel['name'])
        if channel['name'] == '山东卫视': return (1, channel['name'])
        if channel['group'] == '央视频道': return (2, channel['name'])
        if channel['group'] == '山东频道': return (3, channel['name'])
        if channel['group'] == '广播频道': return (4, channel['name'])
        return (5, channel['name'])
    
    channels.sort(key=sort_key)

    def move_channel(ch_list, name, after_name, new_group=None):
        src_idx = next((i for i, ch in enumerate(ch_list) if ch['name'] == name), None)
        if src_idx is not None:
            channel = ch_list.pop(src_idx)
            if new_group: channel['group'] = new_group
            dst_idx = next((i for i, ch in enumerate(ch_list) if ch['name'] == after_name), None)
            if dst_idx is not None:
                ch_list.insert(dst_idx + 1, channel)
                print(f"已将 {name} 移动到 {after_name} 后面 (位置: {dst_idx + 1})")
            else:
                ch_list.append(channel)
                print(f"未找到目标频道 {after_name}，已将 {name} 移动到列表末尾")
        else:
            print(f"未找到源频道 {name}")

    move_channel(channels, 'CCTV4欧洲', '山东少儿')
    move_channel(channels, 'CCTV4美洲', '山东少儿')
    move_channel(channels, '山东经济广播', '', '广播频道')
    return channels

def convert_urls(channels):
    r2h_channels = []
    nofcc_channels = []
    for ch in channels:
        # R2H conversion
        r2h_url = re.sub(r'rtsp://([^?]+)', r'http://192.168.100.1:5140/rtsp/\1', ch['url'])
        r2h_url = re.sub(r'\$\{\{(b|e)yyyyMMddHHmmss:utc\}\}', r'$\{\{\1yyyyMMddHHmmss\}\}', r2h_url)
        r2h_url = r2h_url + '&r2h-seek-offset=-28800'
        r2h_channels.append({**ch, 'url': r2h_url})

        # NoFCC conversion
        nofcc_url = re.sub(r'\$\{\{(b|e)yyyyMMddHHmmss:utc\}\}', r'$\{\{\1yyyyMMddHHmmss\}\}', ch['url'])
        nofcc_channels.append({**ch, 'url': nofcc_url})
        
    return r2h_channels, nofcc_channels

def save_m3u(extm3u_line, channels, output_path):
    ensure_dir_exists(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(extm3u_line + '\n')
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="{ch["group"]}" tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')

# --- 主程序 ---
if __name__ == "__main__":
    print("处理组播源...")
    
    last_hash = load_last_hash()
    source_content = download_file(SOURCE_URL)
    if not source_content:
        print("由于下载失败，停止处理。")
        exit(1)
        
    current_hash = get_file_hash(source_content)
    
    if current_hash == last_hash:
        print("源文件未发生变化，跳过处理。")
    else:
        print(f"源文件发生变化: 旧哈希 {last_hash[:8] if last_hash else 'N/A'}... -> 新哈希 {current_hash[:8]}...")
        
        # --- 原始处理逻辑 ---
        extm3u_line, channels = parse_m3u(source_content)
        print(f"解析完成，共 {len(channels)} 个频道")
        
        print("开始处理频道排序和分类...")
        processed_channels = process_channels(channels)
        print("频道排序处理完成")

        print("开始处理URL转换...")
        r2h_channels, nofcc_channels = convert_urls(processed_channels)
        print("URL转换完成")
        
        save_m3u(extm3u_line, r2h_channels, OUTPUT_PATH_R2H)
        save_m3u(extm3u_line, nofcc_channels, OUTPUT_PATH_NOFCC)
        print("处理完成")

    # 5. 【关键】更新哈希文件
    save_current_hash(current_hash)
