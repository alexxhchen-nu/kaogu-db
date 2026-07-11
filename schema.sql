-- 考古墓葬数据库 Schema
-- 设计目标：支持 OCR 提取数据导入、GIS 可视化、ML 训练数据关联
-- 创建日期：2026-07-11

-- ============================================================
-- 1. 报告/来源
-- ============================================================
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,                    -- 报告标题，如"满城汉墓发掘报告"
    authors TEXT,                           -- 作者
    publication TEXT,                       -- 刊物/出版社
    year INTEGER,                           -- 出版年份
    volume TEXT,                            -- 卷期
    pages TEXT,                             -- 页码范围
    pdf_url TEXT,                           -- R2/BunnyCDN 中的 PDF 路径
    csv_url TEXT,                           -- 预解析 CSV 路径（如有）
    ocr_status TEXT DEFAULT 'pending',      -- pending/processing/done/error
    ocr_engine TEXT,                        -- 使用的 OCR 引擎
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. 遗址/发掘地点
-- ============================================================
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                     -- 遗址名称
    province TEXT,                          -- 省份
    city TEXT,                              -- 市
    district TEXT,                          -- 区县
    town TEXT,                              -- 乡镇
    village TEXT,                           -- 村
    latitude REAL,                          -- 纬度（WGS84）
    longitude REAL,                         -- 经度（WGS84）
    altitude REAL,                          -- 海拔（米）
    period TEXT,                            -- 主要时期
    description TEXT,                       -- 遗址描述
    discovery_year INTEGER,                 -- 发现年份
    excavation_years TEXT,                  -- 发掘年份范围
    protection_level TEXT,                  -- 保护级别（国保/省保/市保）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 为 GIS 查询创建空间索引
CREATE INDEX idx_sites_coords ON sites(latitude, longitude);

-- ============================================================
-- 3. 墓葬
-- ============================================================
CREATE TABLE tombs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER REFERENCES reports(id),
    site_id INTEGER REFERENCES sites(id),
    tomb_number TEXT NOT NULL,              -- 墓葬编号，如 M1, M5, M23
    dynasty TEXT,                           -- 朝代
    period TEXT,                            -- 具体时期，如"战国晚期"
    date_notes TEXT,                        -- 年代判定依据
    orientation TEXT,                       -- 墓向，如"185°"或"南北向"
    tomb_type TEXT,                         -- 墓葬形制：土坑竖穴墓/土洞墓/砖室墓/石室墓
    chamber_count INTEGER,                 -- 墓室数量
    length_m REAL,                          -- 墓口长（米）
    width_m REAL,                           -- 墓口宽（米）
    depth_m REAL,                           -- 墓深（米）
    area_m2 REAL,                           -- 墓口面积（平方米，可计算）
    fill_soil TEXT,                         -- 填土描述
    burial_type TEXT,                       -- 葬式：仰身直肢/侧身屈肢/etc
    occupants INTEGER,                      -- 人骨数量
    disturbanced TEXT,                      -- 盗扰情况
    notes TEXT,                             -- 其他备注
    latitude REAL,                          -- 精确坐标（如有）
    longitude REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(report_id, tomb_number)          -- 同一报告中墓号唯一
);

CREATE INDEX idx_tombs_report ON tombs(report_id);
CREATE INDEX idx_tombs_site ON tombs(site_id);
CREATE INDEX idx_tombs_dynasty ON tombs(dynasty);
CREATE INDEX idx_tombs_type ON tombs(tomb_type);
CREATE INDEX idx_tombs_coords ON tombs(latitude, longitude);

-- ============================================================
-- 4. 器物材质分类（枚举表）
-- ============================================================
CREATE TABLE material_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,              -- 陶器/青铜器/铁器/玉石器/骨角牙器/漆木器/金银器/货币/其他
    description TEXT
);

INSERT INTO material_categories (name) VALUES
    ('陶器'), ('青铜器'), ('铁器'), ('玉石器'),
    ('骨角牙器'), ('漆木器'), ('金银器'), ('货币'), ('其他');

-- ============================================================
-- 5. 器物器型分类（枚举表）
-- ============================================================
CREATE TABLE vessel_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,              -- 罐/壶/鼎/剑/戈/璧/etc
    category TEXT,                          -- 容器类/兵器类/工具类/装饰类/车马器/乐器类/印章类
    description TEXT
);

INSERT INTO vessel_types (name, category) VALUES
    -- 容器类
    ('鼎', '容器类'), ('罐', '容器类'), ('壶', '容器类'), ('瓶', '容器类'),
    ('盆', '容器类'), ('碗', '容器类'), ('盘', '容器类'), ('杯', '容器类'),
    ('尊', '容器类'), ('罍', '容器类'), ('瓮', '容器类'), ('鬲', '容器类'),
    ('豆', '容器类'), ('簋', '容器类'), ('爵', '容器类'), ('斝', '容器类'),
    ('觚', '容器类'),
    -- 兵器类
    ('戈', '兵器类'), ('矛', '兵器类'), ('剑', '兵器类'), ('刀', '兵器类'),
    ('镞', '兵器类'), ('戟', '兵器类'), ('弩机', '兵器类'),
    -- 工具类
    ('斧', '工具类'), ('锛', '工具类'), ('凿', '工具类'), ('铲', '工具类'),
    ('锄', '工具类'), ('镰', '工具类'), ('纺轮', '工具类'), ('锥', '工具类'),
    -- 装饰类
    ('璧', '装饰类'), ('琮', '装饰类'), ('璜', '装饰类'), ('玦', '装饰类'),
    ('环', '装饰类'), ('串珠', '装饰类'), ('坠饰', '装饰类'),
    ('带钩', '装饰类'), ('带饰', '装饰类'), ('耳环', '装饰类'), ('手镯', '装饰类'),
    -- 车马器
    ('车軎', '车马器'), ('马衔', '车马器'), ('节约', '车马器'), ('铜泡', '车马器'),
    -- 乐器类
    ('铃', '乐器类'), ('鼓', '乐器类'), ('磬', '乐器类'), ('瑟', '乐器类'),
    -- 印章类
    ('官印', '印章类'), ('私印', '印章类'), ('肖形印', '印章类');

-- ============================================================
-- 6. 随葬器物
-- ============================================================
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tomb_id INTEGER NOT NULL REFERENCES tombs(id),
    artifact_number TEXT NOT NULL,          -- 器物编号，如 M1:1, M1:2
    name TEXT NOT NULL,                     -- 器物名称，如"陶罐"
    material_category TEXT,                 -- 材质分类（关联 material_categories）
    vessel_type TEXT,                       -- 器型（关联 vessel_types）
    quantity INTEGER DEFAULT 1,             -- 数量
    description TEXT,                       -- 特征描述
    condition TEXT,                         -- 保存状态：完整/破碎/残损
    decoration TEXT,                        -- 纹饰描述
    dimensions TEXT,                        -- 尺寸描述
    weight_g REAL,                          -- 重量（克）
    color TEXT,                             -- 颜色
    fabrication TEXT,                       -- 制作工艺：轮制/手制/模制
    image_url TEXT,                         -- 图片 URL（如有）
    notes TEXT,                             -- 备注
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tomb_id, artifact_number)        -- 同一墓葬中器物号唯一
);

CREATE INDEX idx_artifacts_tomb ON artifacts(tomb_id);
CREATE INDEX idx_artifacts_material ON artifacts(material_category);
CREATE INDEX idx_artifacts_vessel ON artifacts(vessel_type);

-- ============================================================
-- 7. 图片资源
-- ============================================================
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER REFERENCES artifacts(id),
    tomb_id INTEGER REFERENCES tombs(id),
    site_id INTEGER REFERENCES sites(id),
    url TEXT NOT NULL,                      -- 图片 URL（R2/BunnyCDN）
    source TEXT,                            -- 来源：xunzhilu/遗址照片/报告插图
    caption TEXT,                           -- 图片说明
    width INTEGER,
    height INTEGER,
    format TEXT,                            -- jpg/png/webp
    file_size_kb INTEGER,
    is_primary BOOLEAN DEFAULT 0,           -- 是否为主图
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_images_artifact ON images(artifact_id);
CREATE INDEX idx_images_tomb ON images(tomb_id);

-- ============================================================
-- 8. ML 训练数据集
-- ============================================================
CREATE TABLE ml_datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                     -- 数据集名称
    source TEXT,                            -- 来源：robolow/custom/kaggle
    format TEXT,                            -- YOLO/COCO/VOC
    url TEXT,                               -- 数据集 URL
    image_count INTEGER,                    -- 图片数量
    class_count INTEGER,                    -- 类别数量
    classes TEXT,                            -- 类别列表（JSON）
    description TEXT,
    license TEXT,
    created_at DATASET DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 9. 器物-数据集关联（用于 ML 训练）
-- ============================================================
CREATE TABLE artifact_dataset_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER REFERENCES artifacts(id),
    dataset_id INTEGER REFERENCES ml_datasets(id),
    image_id INTEGER REFERENCES images(id),
    class_label TEXT,                       -- 在数据集中的类别标签
    bbox_x REAL,                            -- 边界框坐标（归一化）
    bbox_y REAL,
    bbox_width REAL,
    bbox_height REAL,
    confidence REAL,                        -- 标注置信度
    annotator TEXT,                         -- 标注者
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 10. 提取日志（OCR 追踪）
-- ============================================================
CREATE TABLE extraction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER REFERENCES reports(id),
    tomb_id INTEGER REFERENCES tombs(id),
    step TEXT NOT NULL,                     -- ocr/parse/validate/import
    status TEXT NOT NULL,                   -- success/error/warning
    engine TEXT,                            -- 使用的工具/模型
    input_text TEXT,                        -- 输入文本片段
    output_json TEXT,                       -- 输出 JSON
    error_message TEXT,
    duration_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_report ON extraction_logs(report_id);
CREATE INDEX idx_logs_status ON extraction_logs(status);

-- ============================================================
-- 11. 用户标注/修正
-- ============================================================
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,               -- 目标表：tombs/artifacts/sites
    record_id INTEGER NOT NULL,             -- 目标记录 ID
    field_name TEXT NOT NULL,               -- 修改的字段
    old_value TEXT,                         -- 原值
    new_value TEXT,                         -- 新值
    annotator TEXT,                         -- 标注者
    reason TEXT,                            -- 修改原因
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 视图：墓葬概览（用于 GIS 可视化）
-- ============================================================
CREATE VIEW tomb_overview AS
SELECT
    t.id,
    t.tomb_number,
    t.dynasty,
    t.period,
    t.tomb_type,
    t.length_m,
    t.width_m,
    t.depth_m,
    t.area_m2,
    t.orientation,
    s.name AS site_name,
    s.province,
    s.city,
    s.latitude,
    s.longitude,
    r.title AS report_title,
    COUNT(a.id) AS artifact_count,
    GROUP_CONCAT(DISTINCT a.material_category) AS materials
FROM tombs t
LEFT JOIN sites s ON t.site_id = s.id
LEFT JOIN reports r ON t.report_id = r.id
LEFT JOIN artifacts a ON a.tomb_id = t.id
GROUP BY t.id;

-- ============================================================
-- 视图：器物统计（用于分析）
-- ============================================================
CREATE VIEW artifact_stats AS
SELECT
    a.material_category,
    a.vessel_type,
    COUNT(*) AS count,
    COUNT(DISTINCT a.tomb_id) AS tomb_count,
    COUNT(DISTINCT t.site_id) AS site_count
FROM artifacts a
JOIN tombs t ON a.tomb_id = t.id
GROUP BY a.material_category, a.vessel_type
ORDER BY count DESC;

-- ============================================================
-- 视图：报告处理进度
-- ============================================================
CREATE VIEW report_progress AS
SELECT
    r.id,
    r.title,
    r.year,
    r.ocr_status,
    COUNT(DISTINCT t.id) AS tomb_count,
    COUNT(DISTINCT a.id) AS artifact_count,
    MAX(e.created_at) AS last_extraction
FROM reports r
LEFT JOIN tombs t ON t.report_id = r.id
LEFT JOIN artifacts a ON a.tomb_id = t.id
LEFT JOIN extraction_logs e ON e.report_id = r.id
GROUP BY r.id;
