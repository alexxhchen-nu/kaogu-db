"""
CSV 导入脚本 — 从 BunnyCDN 下载预解析 CSV 并导入 SQLite

Usage:
  python import_csv.py                    # 下载并导入所有 CSV
  python import_csv.py --local file.csv   # 导入本地 CSV
  python import_csv.py --dry-run          # 预览不写入
"""
import os, sys, csv, sqlite3, argparse, json, io
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

# BunnyCDN credentials
BUNNY_STORAGE_KEY = os.environ.get("BUNNY_STORAGE_KEY", "406e504b-2f01-4da0-8e01c3c392c8-4221-463b")
BUNNY_ENDPOINT = os.environ.get("BUNNY_ENDPOINT", "https://sg.storage.bunnycdn.com/xiaohanchen")
DB_PATH = os.environ.get("KAOGU_DB", "kaogu.db")

CSV_FILES = [
    "hebei-1.csv", "hebei-2.csv", "hebei-3.csv",
    "nsbd-2.csv", "nsbd-3.csv", "nsbd-5.csv", "nsbd-6.csv",
    "nsbd-8.csv", "nsbd-10.csv", "nsbd-11.csv",
]

def download_csv(filename):
    """从 BunnyCDN 下载 CSV"""
    # URL-encode the Chinese characters in the path
    path = quote(f"解析结果_csv/{filename}")
    url = f"{BUNNY_ENDPOINT}/{path}"
    req = Request(url, headers={"AccessKey": BUNNY_STORAGE_KEY})
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8-sig")  # utf-8-sig handles BOM
    except Exception as e:
        print(f"  ❌ 下载失败 {filename}: {e}")
        return None

def init_db(db_path):
    """初始化数据库"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # 检查数据库是否已初始化
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
    if not cursor.fetchone():
        schema_path = Path(__file__).parent.parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path) as f:
                conn.executescript(f.read())
    
    conn.commit()
    return conn

def get_or_create_report(conn, title, series=None):
    """获取或创建报告记录"""
    cursor = conn.execute("SELECT id FROM reports WHERE title = ?", (title,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # 检查是否有 series 列
    cursor = conn.execute("PRAGMA table_info(reports)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'series' in columns:
        cursor = conn.execute(
            "INSERT INTO reports (title, series, ocr_status) VALUES (?, ?, 'done')",
            (title, series)
        )
    else:
        cursor = conn.execute(
            "INSERT INTO reports (title, ocr_status) VALUES (?, 'done')",
            (title,)
        )
    conn.commit()
    return cursor.lastrowid

def get_or_create_site(conn, location, report_id):
    """获取或创建遗址记录"""
    if not location:
        return None
    
    # 尝试从位置中提取省/市/县
    province = None
    city = None
    district = None
    
    # 简单解析（可以根据需要改进）
    if '省' in location:
        parts = location.split('省')
        province = parts[0] + '省'
        if '市' in parts[1]:
            city_parts = parts[1].split('市')
            city = city_parts[0] + '市'
            district = city_parts[1] if len(city_parts) > 1 else None
    
    cursor = conn.execute("SELECT id FROM sites WHERE name = ?", (location,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # 检查是否有 report_id 列
    cursor = conn.execute("PRAGMA table_info(sites)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'report_id' in columns:
        cursor = conn.execute(
            """INSERT INTO sites (name, province, city, district, report_id)
               VALUES (?, ?, ?, ?, ?)""",
            (location, province, city, district, report_id)
        )
    else:
        cursor = conn.execute(
            """INSERT INTO sites (name, province, city, district)
               VALUES (?, ?, ?, ?)""",
            (location, province, city, district)
        )
    conn.commit()
    return cursor.lastrowid

def get_or_create_tomb(conn, tomb_number, report_id, site_id, row_data):
    """获取或创建墓葬记录"""
    cursor = conn.execute(
        "SELECT id FROM tombs WHERE tomb_number = ? AND report_id = ?",
        (tomb_number, report_id)
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0]
    
    # 解析尺寸
    length = float(row_data.get('墓口长', 0) or 0) or None
    width = float(row_data.get('墓口宽', 0) or 0) or None
    depth = float(row_data.get('墓深', 0) or 0) or None
    
    cursor = conn.execute(
        """INSERT INTO tombs 
           (tomb_number, report_id, site_id, dynasty, orientation, tomb_type,
            length_m, width_m, depth_m, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            tomb_number,
            report_id,
            site_id,
            row_data.get('年代'),
            row_data.get('墓向'),
            row_data.get('墓葬形制'),
            length,
            width,
            depth,
            row_data.get('备注'),
        )
    )
    conn.commit()
    return cursor.lastrowid

def insert_artifact(conn, tomb_id, row_data):
    """插入器物记录"""
    artifact_number = row_data.get('器物编号')
    name = row_data.get('器物名称', '未知')
    material = row_data.get('材质')
    vessel_type = row_data.get('器型')
    quantity = int(row_data.get('数量', 1) or 1)
    description = row_data.get('特征描述')
    
    try:
        conn.execute(
            """INSERT INTO artifacts 
               (artifact_number, tomb_id, name, material_category, vessel_type, quantity, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (artifact_number, tomb_id, name, material, vessel_type, quantity, description)
        )
    except sqlite3.IntegrityError:
        # 已存在，跳过
        pass

def import_csv_data(conn, csv_content, source_name, dry_run=False):
    """导入 CSV 数据"""
    reader = csv.DictReader(io.StringIO(csv_content))
    
    # 确定报告名称和系列
    if 'hebei' in source_name.lower():
        report_title = f"河北省考古文集（{source_name.replace('.csv', '').replace('hebei-', '')}）"
        series = "河北省考古文集"
    elif 'nsbd' in source_name.lower():
        report_title = f"南水北调中线工程文物保护项目（{source_name.replace('.csv', '').replace('nsbd-', '')}）"
        series = "南水北调"
    else:
        report_title = source_name.replace('.csv', '')
        series = None
    
    print(f"\n📄 处理: {report_title}")
    
    if not dry_run:
        report_id = get_or_create_report(conn, report_title, series)
    
    tomb_count = 0
    artifact_count = 0
    seen_tombs = set()
    
    for row in reader:
        tomb_number = row.get('墓葬编号', '').strip()
        if not tomb_number:
            continue
        
        # 创建墓葬
        if tomb_number not in seen_tombs:
            seen_tombs.add(tomb_number)
            tomb_count += 1
            
            if not dry_run:
                site_id = get_or_create_site(conn, row.get('发掘位置'), report_id)
                tomb_id = get_or_create_tomb(conn, tomb_number, report_id, site_id, row)
            else:
                print(f"  墓葬: {tomb_number} | {row.get('年代', '?')} | "
                      f"{row.get('墓葬形制', '?')} | "
                      f"{row.get('墓口长', '?')}x{row.get('墓口宽', '?')}x{row.get('墓深', '?')}m")
        
        # 创建器物
        artifact_name = row.get('器物名称', '').strip()
        if artifact_name:
            artifact_count += 1
            if not dry_run:
                insert_artifact(conn, tomb_id, row)
            else:
                print(f"    器物: {row.get('器物编号', '?')} | {artifact_name} | "
                      f"{row.get('材质', '?')} | {row.get('器型', '?')} | "
                      f"x{row.get('数量', 1)}")
    
    if not dry_run:
        conn.commit()
    
    print(f"  ✅ {tomb_count} 座墓葬, {artifact_count} 件器物")
    return tomb_count, artifact_count

def main():
    parser = argparse.ArgumentParser(description="导入预解析 CSV 到 SQLite")
    parser.add_argument("--local", help="导入本地 CSV 文件")
    parser.add_argument("--db", default=DB_PATH, help="数据库路径")
    parser.add_argument("--dry-run", action="store_true", help="预览不写入")
    args = parser.parse_args()
    
    conn = init_db(args.db)
    
    total_tombs = 0
    total_artifacts = 0
    
    if args.local:
        # 导入本地文件
        with open(args.local, encoding="utf-8-sig") as f:
            content = f.read()
        tombs, artifacts = import_csv_data(conn, content, Path(args.local).name, args.dry_run)
        total_tombs += tombs
        total_artifacts += artifacts
    else:
        # 从 BunnyCDN 下载并导入
        print("📥 从 BunnyCDN 下载 CSV 文件...")
        for filename in CSV_FILES:
            content = download_csv(filename)
            if content:
                tombs, artifacts = import_csv_data(conn, content, filename, args.dry_run)
                total_tombs += tombs
                total_artifacts += artifacts
    
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"📊 总计: {total_tombs} 座墓葬, {total_artifacts} 件器物")
    if not args.dry_run:
        print(f"   数据库: {args.db}")

if __name__ == "__main__":
    main()
