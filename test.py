import sqlite3
import json
import os
import csv

# 获取当前用户的路径
user_path = os.path.expanduser('~')

# 构建数据库文件路径
db_path = os.path.join(user_path, 'AppData', 'Local', 'NetEase', 'CloudMusic', 'Library', 'webdb.dat')

# 创建导出文件夹
output_dir = "exported_playlists"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

# 连接数据库
print(f"Opening database at: {db_path}")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 执行SQL查询
    print("Executing query...")
    cursor.execute("SELECT pid, playlist FROM web_playlist")
    
    # 获取结果
    playlists = cursor.fetchall()
    print(f"Found {len(playlists)} playlists.")
except Exception as e:
    print(f"Error: {e}")
    exit(1)

# 用于存储所有歌单的汇总数据
all_playlists_rows = []

for playlist in playlists:
    playlist_id = playlist[0]
    playlist_json = playlist[1]
    
    # 解析JSON字符串
    try:
        playlist_data = json.loads(playlist_json)
        playlist_name = playlist_data.get("name", f"Unknown_Playlist_{playlist_id}")
        is_subscribed = playlist_data.get("subscribed", False)
        playlist_type = "我收藏的" if is_subscribed else "我创建的"
        
        print(f"Processing playlist: {playlist_name} (ID: {playlist_id}, Type: {playlist_type})")
        
        # 查询歌曲ID列表
        cursor.execute("SELECT tid FROM web_playlist_track WHERE pid = ? ORDER BY [order]", (playlist_id,))
        track_rows = cursor.fetchall()
        track_ids = [row[0] for row in track_rows]
        
        # 查询歌曲详细信息
        track_details = []
        for track_id in track_ids:
            cursor.execute("SELECT track FROM web_track WHERE tid = ?", (track_id,))
            track_info = cursor.fetchone()
            if track_info:
                track_json = track_info[0]
                try:
                    track_data = json.loads(track_json)
                    track_details.append(track_data)
                except json.JSONDecodeError:
                    print(f"  Warning: Could not parse JSON for track {track_id}")
        
        # 将歌单信息和歌曲详细信息写入CSV文件
        safe_playlist_name = "".join([c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        # 为了区分，在文件名前加上类型
        file_name = os.path.join(output_dir, f"{playlist_type}_{safe_playlist_name}.csv")
        
        # 准备当前歌单的所有行数据
        current_playlist_rows = []
        
        for index, track in enumerate(track_details, start=1):
            track_name = track.get('name', 'Unknown')
            
            artists_list = track.get('artists', [])
            artists = [artist.get('name', 'Unknown') for artist in artists_list]
            artists_str = ', '.join(artists)
            
            album_data = track.get('album', {})
            album_name = album_data.get('name', '') if album_data else ''
            
            # 构建一行数据：序号, 标题, 歌手, 专辑, 列表名称, 歌单类型
            row = [index, track_name, artists_str, album_name, playlist_name, playlist_type]
            current_playlist_rows.append(row)
            
        # 将当前歌单数据添加到汇总列表
        all_playlists_rows.extend(current_playlist_rows)

        # 写入单个歌单CSV
        with open(file_name, "w", encoding="utf-8-sig", newline='') as file:
            writer = csv.writer(file)
            # 写入表头
            writer.writerow(["序号", "标题", "歌手", "专辑", "列表名称", "歌单类型"])
            writer.writerows(current_playlist_rows)
                
    except json.JSONDecodeError:
        print(f"Error parsing playlist JSON for ID {playlist_id}")
    except Exception as e:
        print(f"Error processing playlist {playlist_id}: {e}")

# 写入汇总 CSV 文件
summary_file_name = os.path.join(output_dir, "所有歌单汇总.csv")
try:
    with open(summary_file_name, "w", encoding="utf-8-sig", newline='') as file:
        writer = csv.writer(file)
        # 写入表头
        writer.writerow(["序号", "标题", "歌手", "专辑", "列表名称", "歌单类型"])
        writer.writerows(all_playlists_rows)
    print(f"所有歌单汇总已导出到: {summary_file_name}")
except Exception as e:
    print(f"Error writing summary file: {e}")

# 关闭连接
conn.close()

print(f"歌单列表已导出到文件夹: {output_dir}")
