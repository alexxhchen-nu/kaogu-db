"""
OCR Pipeline for 考古墓葬数据库
PDF → Baidu OCR → 提取墓葬信息 → 写入 SQLite

Usage:
  python ocr_pipeline.py <pdf_path>           # 处理单个 PDF
  python ocr_pipeline.py --batch data/pdfs/   # 批量处理目录
  python ocr_pipeline.py --resume              # 继续未完成的任务
"""
import os, sys, json, base64, re, time, sqlite3, argparse
from pathlib import Path
import requests
import fitz  # PyMuPDF

# --- Config ---
BAIDU_API_KEY = os.environ.get("BAIDU_OCR_API_KEY", "FDAyahVa9jMc64InAa8SzJib")
BAIDU_SECRET = os.environ.get("BAIDU_OCR_SECRET_KEY", "pIZZY81GjRyY6IUYvQQIHCfyvx94Eh2E")
DB_PATH = os.environ.get("KAOGU_DB", "kaogu.db")
DPI = 100  # 100 DPI keeps image ≤ 2000px for Baidu OCR
START_PAGE = 30  # Skip covers/TOC

# --- Baidu OCR ---
def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET,
    }
    resp = requests.post(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]

def ocr_image(token, image_bytes):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={token}"
    img_b64 = base64.b64encode(image_bytes).decode()
    resp = requests.post(
        url,
        data={"image": img_b64},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    result = resp.json()
    if "words_result" in result:
        return "\n".join(w["words"] for w in result["words_result"])
    return ""

# --- Extraction patterns ---
TOMB_PATTERNS = [
    # M1, M12, m001
    re.compile(r'[Mm](\d+)号?墓?'),
    # 一号墓, 十二号墓
    re.compile(r'([一二三四五六七八九十百]+)号墓'),
    # 第1号墓, 第12号墓
    re.compile(r'第(\d+)号墓'),
    # M1: 格式（器物编号前缀）
    re.compile(r'[Mm](\d+)[：:]'),
]

DYNASTY_KEYWORDS = {
    '商': '商代', '殷': '商代', '夏': '夏代',
    '西周': '西周', '东周': '东周', '春秋': '春秋', '战国': '战国',
    '秦': '秦代', '汉': '汉代', '西汉': '西汉', '东汉': '东汉',
    '三国': '三国', '魏晋': '魏晋', '南北朝': '南北朝',
    '隋': '隋代', '唐': '唐代', '宋': '宋代', '元': '元代', '明': '明代', '清': '清代',
}

STRUCTURE_KEYWORDS = [
    '土坑竖穴', '土洞墓', '砖室墓', '石室墓', '木椁墓', '崖墓',
    '竖穴土坑', '砖室', '石室', '土坑', '洞室',
]

DIRECTION_PATTERN = re.compile(r'(?:方向|朝向)[：:]?\s*(\d+\.?\d*)[°度]|(?:南北|东西|南偏[东西]|北偏[东西])向?')

DIM_PATTERN = re.compile(r'(?:长|宽|深|高)[：:]?\s*(\d+\.?\d*)\s*(?:米|m)')

ARTIFACT_PATTERN = re.compile(
    r'([Mm]\d+[：:]?\d*)'  # 器物编号 M1:1
    r'|'
    r'(陶|铜|铁|玉|石|骨|漆|木|金|银|贝|玛瑙|绿松)(器|罐|壶|鼎|豆|簋|爵|斝|觚|盘|盆|碗|杯|尊|罍|瓮|鬲|'
    r'剑|戈|矛|刀|镞|戟|弩机|璧|琮|璜|玦|环|串珠|坠饰|带钩|耳环|手镯|铃|鼓|磬|釜|甑|灯|炉|镜|印|钱币|五铢|半两)'
)

def extract_tombs_from_text(text, page_num):
    """从一页 OCR 文本中提取墓葬信息"""
    results = []
    lines = text.split('\n')
    
    # 检测墓葬编号
    for line in lines:
        for pat in TOMB_PATTERNS:
            match = pat.search(line)
            if match:
                tomb_num = match.group(1) if match.lastindex else match.group(0)
                # 标准化墓葬编号
                if tomb_num.isdigit():
                    tomb_id = f"M{tomb_num}"
                else:
                    tomb_id = tomb_num
                
                tomb = {
                    'tomb_number': tomb_id,
                    'page': page_num,
                    'raw_text': line,
                    'dynasty': None,
                    'direction': None,
                    'structure': None,
                    'length': None,
                    'width': None,
                    'depth': None,
                    'artifacts': [],
                }
                
                # 提取朝代
                for kw, dynasty in DYNASTY_KEYWORDS.items():
                    if kw in text:
                        tomb['dynasty'] = dynasty
                        break
                
                # 提取墓向
                dir_match = DIRECTION_PATTERN.search(text)
                if dir_match:
                    tomb['direction'] = dir_match.group(0)
                
                # 提取形制
                for kw in STRUCTURE_KEYWORDS:
                    if kw in text:
                        tomb['structure'] = kw
                        break
                
                # 提取尺寸
                dims = DIM_PATTERN.findall(text)
                if len(dims) >= 3:
                    tomb['length'] = float(dims[0])
                    tomb['width'] = float(dims[1])
                    tomb['depth'] = float(dims[2])
                elif len(dims) == 2:
                    tomb['length'] = float(dims[0])
                    tomb['width'] = float(dims[1])
                
                # 提取器物
                for art_match in ARTIFACT_PATTERN.finditer(text):
                    art_text = art_match.group(0)
                    if art_text.startswith(('M', 'm')):
                        # 器物编号
                        tomb['artifacts'].append({'number': art_text, 'name': None, 'material': None})
                    else:
                        # 器物名称
                        material = art_match.group(2) if art_match.lastindex >= 2 else None
                        name = art_match.group(3) if art_match.lastindex >= 3 else art_text
                        tomb['artifacts'].append({
                            'number': None,
                            'name': name,
                            'material': material,
                        })
                
                results.append(tomb)
                break  # 每行只匹配第一个墓葬
    
    return results

def init_db(db_path):
    """初始化数据库"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    
    schema_path = Path(__file__).parent.parent / "schema.sql"
    if schema_path.exists():
        with open(schema_path) as f:
            conn.executescript(f.read())
    
    conn.commit()
    return conn

def insert_report(conn, title, pdf_path):
    """插入或获取报告记录"""
    cursor = conn.execute(
        "SELECT id FROM reports WHERE pdf_path = ?", (pdf_path,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    
    cursor = conn.execute(
        "INSERT INTO reports (title, pdf_path, ocr_status) VALUES (?, ?, 'processing')",
        (title, pdf_path)
    )
    conn.commit()
    return cursor.lastrowid

def insert_tomb(conn, report_id, tomb_data):
    """插入墓葬记录"""
    cursor = conn.execute(
        """INSERT INTO tombs 
           (tomb_number, report_id, dynasty, direction, structure, length, width, depth, raw_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            tomb_data['tomb_number'],
            report_id,
            tomb_data.get('dynasty'),
            tomb_data.get('direction'),
            tomb_data.get('structure'),
            tomb_data.get('length'),
            tomb_data.get('width'),
            tomb_data.get('depth'),
            tomb_data.get('raw_text'),
        )
    )
    return cursor.lastrowid

def insert_artifact(conn, tomb_id, artifact_data):
    """插入器物记录"""
    name = artifact_data.get('name') or artifact_data.get('number') or '未知'
    conn.execute(
        """INSERT INTO artifacts 
           (artifact_number, tomb_id, name, material, vessel_type)
           VALUES (?, ?, ?, ?, ?)""",
        (
            artifact_data.get('number'),
            tomb_id,
            name,
            artifact_data.get('material'),
            artifact_data.get('name'),  # vessel_type 从 name 推断
        )
    )

def update_report_status(conn, report_id, status, tomb_count=0, artifact_count=0):
    """更新报告处理状态"""
    conn.execute(
        "UPDATE reports SET ocr_status = ? WHERE id = ?",
        (status, report_id)
    )
    conn.execute(
        """INSERT INTO extraction_logs (report_id, status, tomb_count, artifact_count)
           VALUES (?, ?, ?, ?)""",
        (report_id, status, tomb_count, artifact_count)
    )
    conn.commit()

def process_pdf(conn, pdf_path, token, start_page=START_PAGE, max_pages=None):
    """处理单个 PDF"""
    pdf_path = str(pdf_path)
    title = Path(pdf_path).stem
    
    # 检查是否已处理
    cursor = conn.execute(
        "SELECT id, ocr_status FROM reports WHERE pdf_path = ?", (pdf_path,)
    )
    row = cursor.fetchone()
    if row and row[1] == 'done':
        print(f"  ⏭️  已完成: {title}")
        return row[0]
    
    report_id = insert_report(conn, title, pdf_path)
    
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    end_page = min(start_page + (max_pages or 200), total_pages)
    
    print(f"\n📄 处理: {title}")
    print(f"   页数: {start_page+1}-{end_page} / {total_pages}")
    
    tomb_count = 0
    artifact_count = 0
    
    for i in range(start_page, end_page):
        page = doc[i]
        pix = page.get_pixmap(dpi=DPI)
        img_bytes = pix.tobytes("png")
        
        try:
            text = ocr_image(token, img_bytes)
        except Exception as e:
            print(f"   ❌ OCR 错误 (第{i+1}页): {e}")
            continue
        
        if not text.strip():
            continue
        
        tombs = extract_tombs_from_text(text, i + 1)
        
        for tomb_data in tombs:
            tomb_id = insert_tomb(conn, report_id, tomb_data)
            tomb_count += 1
            
            for art_data in tomb_data.get('artifacts', []):
                if art_data.get('name') or art_data.get('number'):
                    insert_artifact(conn, tomb_id, art_data)
                    artifact_count += 1
            
            print(f"   第{i+1}页: {tomb_data['tomb_number']} — "
                  f"{len(tomb_data['artifacts'])} 件器物")
        
        # 每 10 页提交一次
        if (i + 1) % 10 == 0:
            conn.commit()
            print(f"   进度: {i+1}/{end_page} 页, {tomb_count} 座墓葬")
        
        time.sleep(0.1)  # Baidu OCR rate limit
    
    doc.close()
    
    update_report_status(conn, report_id, 'done', tomb_count, artifact_count)
    print(f"   ✅ 完成: {tomb_count} 座墓葬, {artifact_count} 件器物")
    
    return report_id

def main():
    parser = argparse.ArgumentParser(description="考古墓葬 OCR 管线")
    parser.add_argument("pdf_path", nargs="?", help="单个 PDF 路径")
    parser.add_argument("--batch", help="批量处理目录")
    parser.add_argument("--db", default=DB_PATH, help="数据库路径")
    parser.add_argument("--start", type=int, default=START_PAGE, help="起始页码")
    parser.add_argument("--max-pages", type=int, help="最大处理页数")
    parser.add_argument("--resume", action="store_true", help="继续未完成的任务")
    args = parser.parse_args()
    
    if not args.pdf_path and not args.batch:
        parser.print_help()
        sys.exit(1)
    
    # 初始化
    conn = init_db(args.db)
    print("🔑 获取 Baidu OCR token...")
    token = get_access_token()
    
    # 收集 PDF 列表
    pdfs = []
    if args.pdf_path:
        pdfs.append(Path(args.pdf_path))
    elif args.batch:
        batch_dir = Path(args.batch)
        pdfs = sorted(batch_dir.glob("*.pdf"))
        print(f"📁 找到 {len(pdfs)} 个 PDF")
    
    # 处理
    total_tombs = 0
    total_artifacts = 0
    
    for pdf in pdfs:
        try:
            report_id = process_pdf(
                conn, pdf, token,
                start_page=args.start,
                max_pages=args.max_pages,
            )
            # 统计
            cursor = conn.execute(
                "SELECT tomb_count, artifact_count FROM extraction_logs WHERE report_id = ? ORDER BY id DESC LIMIT 1",
                (report_id,)
            )
            row = cursor.fetchone()
            if row:
                total_tombs += row[0]
                total_artifacts += row[1]
        except Exception as e:
            print(f"❌ 处理失败 {pdf.name}: {e}")
    
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"📊 总计: {len(pdfs)} 个 PDF")
    print(f"   墓葬: {total_tombs}")
    print(f"   器物: {total_artifacts}")
    print(f"   数据库: {args.db}")

if __name__ == "__main__":
    main()
