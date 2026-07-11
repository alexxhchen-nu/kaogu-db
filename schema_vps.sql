-- 考古墓葬数据库 Schema
-- 支持 OCR 提取、GIS 可视化、ML 训练数据关联

-- 报告/文献
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    year INTEGER,
    publisher TEXT,
    series TEXT,
    volume TEXT,
    pdf_path TEXT,
    pdf_url TEXT,
    total_pages INTEGER,
    ocr_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 遗址
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    province TEXT,
    city TEXT,
    county TEXT,
    longitude REAL,
    latitude REAL,
    period TEXT,
    description TEXT,
    report_id INTEGER REFERENCES reports(id)
);

-- 墓葬
CREATE TABLE IF NOT EXISTS tombs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tomb_number TEXT NOT NULL,
    site_id INTEGER REFERENCES sites(id),
    report_id INTEGER REFERENCES reports(id),
    dynasty TEXT,
    direction TEXT,
    structure TEXT,
    length REAL,
    width REAL,
    depth REAL,
    notes TEXT,
    raw_text TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 随葬器物
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_number TEXT,
    tomb_id INTEGER REFERENCES tombs(id),
    name TEXT NOT NULL,
    material TEXT,
    vessel_type TEXT,
    quantity INTEGER DEFAULT 1,
    description TEXT,
    image_path TEXT,
    ml_dataset_id INTEGER,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 材质分类
CREATE TABLE IF NOT EXISTS material_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- 器型分类
CREATE TABLE IF NOT EXISTS vessel_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    description TEXT
);

-- 图像
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER REFERENCES artifacts(id),
    tomb_id INTEGER REFERENCES tombs(id),
    image_path TEXT NOT NULL,
    image_type TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ML 数据集
CREATE TABLE IF NOT EXISTS ml_datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,
    description TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 器物-数据集映射
CREATE TABLE IF NOT EXISTS artifact_dataset_mapping (
    artifact_id INTEGER REFERENCES artifacts(id),
    dataset_id INTEGER REFERENCES ml_datasets(id),
    split TEXT DEFAULT 'train',
    PRIMARY KEY (artifact_id, dataset_id)
);

-- OCR 提取日志
CREATE TABLE IF NOT EXISTS extraction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER REFERENCES reports(id),
    page_start INTEGER,
    page_end INTEGER,
    status TEXT,
    tomb_count INTEGER,
    artifact_count INTEGER,
    raw_text TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 人工标注/校正
CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    annotator TEXT,
    confidence REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tombs_site ON tombs(site_id);
CREATE INDEX IF NOT EXISTS idx_tombs_report ON tombs(report_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_tomb ON artifacts(tomb_id);
CREATE INDEX IF NOT EXISTS idx_images_artifact ON images(artifact_id);
CREATE INDEX IF NOT EXISTS idx_annotations_record ON annotations(table_name, record_id);

-- 视图：墓葬概览
CREATE VIEW IF NOT EXISTS tomb_overview AS
SELECT 
    t.id, t.tomb_number, t.dynasty, t.direction, t.structure,
    t.length, t.width, t.depth,
    s.name as site_name, s.province, s.city,
    r.title as report_title,
    COUNT(a.id) as artifact_count
FROM tombs t
LEFT JOIN sites s ON t.site_id = s.id
LEFT JOIN reports r ON t.report_id = r.id
LEFT JOIN artifacts a ON a.tomb_id = t.id
GROUP BY t.id;

-- 视图：器物统计
CREATE VIEW IF NOT EXISTS artifact_stats AS
SELECT 
    a.material, a.vessel_type,
    COUNT(*) as count,
    COUNT(DISTINCT a.tomb_id) as tomb_count
FROM artifacts a
GROUP BY a.material, a.vessel_type;

-- 视图：报告进度
CREATE VIEW IF NOT EXISTS report_progress AS
SELECT 
    r.id, r.title, r.ocr_status,
    COUNT(DISTINCT t.id) as tomb_count,
    COUNT(DISTINCT a.id) as artifact_count
FROM reports r
LEFT JOIN tombs t ON t.report_id = r.id
LEFT JOIN artifacts a ON a.tomb_id = t.id
GROUP BY r.id;

-- 初始数据：材质分类
INSERT OR IGNORE INTO material_categories (name, description) VALUES
('陶器', '泥质陶、夹砂陶、釉陶、原始瓷'),
('青铜器', '铜器、青铜器'),
('铁器', '铁器'),
('玉石器', '玉器、石器、玛瑙、绿松石'),
('骨角牙器', '骨器、角器、牙器、贝器'),
('漆木器', '漆器、木器、竹器'),
('金银器', '金器、银器'),
('货币', '铜钱、布币、刀币'),
('其他', '纺织品、粮食、人骨等');

-- 初始数据：器型分类
INSERT OR IGNORE INTO vessel_types (name, category, description) VALUES
('鼎', '容器', '三足两耳礼器'),
('罐', '容器', '圆腹容器'),
('壶', '容器', '长颈容器'),
('瓶', '容器', '细长颈容器'),
('盆', '容器', '敞口浅腹'),
('碗', '容器', '圆形食器'),
('盘', '容器', '浅腹平底'),
('杯', '容器', '小型饮器'),
('尊', '容器', '大型礼器'),
('罍', '容器', '大型盛酒器'),
('瓮', '容器', '大型储容器'),
('鬲', '容器', '袋足炊器'),
('豆', '容器', '高足盘'),
('簋', '容器', '圆腹圈足'),
('爵', '容器', '三足酒器'),
('斝', '容器', '三足温酒器'),
('觚', '容器', '喇叭口酒器'),
('戈', '兵器', '横刃兵器'),
('矛', '兵器', '直刺兵器'),
('剑', '兵器', '双刃短兵器'),
('刀', '兵器', '单刃兵器'),
('镞', '兵器', '箭头'),
('戟', '兵器', '戈矛合体'),
('弩机', '兵器', '远射兵器'),
('斧', '工具', '砍伐工具'),
('锛', '工具', '木工工具'),
('凿', '工具', '穿孔工具'),
('铲', '工具', '农具'),
('锄', '工具', '农具'),
('镰', '工具', '收割工具'),
('纺轮', '工具', '纺织工具'),
('锥', '工具', '穿刺工具'),
('璧', '装饰', '圆形玉器'),
('琮', '装饰', '方柱圆筒玉器'),
('璜', '装饰', '弧形玉器'),
('玦', '装饰', '有缺口的玉环'),
('环', '装饰', '圆形装饰品'),
('串珠', '装饰', '串联珠饰'),
('坠饰', '装饰', '悬挂装饰品'),
('带钩', '装饰', '腰带挂钩'),
('耳环', '装饰', '耳饰'),
('手镯', '装饰', '腕饰'),
('车軎', '车马器', '车轴装饰'),
('马衔', '车马器', '马嚼子'),
('铃', '乐器', '响器'),
('鼓', '乐器', '打击乐器'),
('磬', '乐器', '石制打击乐器');
