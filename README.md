# 考古墓葬数据库设计说明

## 设计目标

1. **支持 OCR 提取数据导入** — 从 228+ PDF 报告中批量提取墓葬信息
2. **GIS 可视化** — 为 Track A（数据库+GIS）提供空间查询支持
3. **ML 训练数据关联** — 为 Track B（图像分类）建立器物-图片-数据集映射
4. **人工审核工作流** — 支持标注、修正、质量追踪

## 核心表结构

### 层级关系

```
reports (报告)
  └── tombs (墓葬)
        └── artifacts (器物)
              └── images (图片)

sites (遗址)
  └── tombs (墓葬)
```

### 关键设计决策

| 决策 | 理由 |
|------|------|
| **报告单独建表** | 一份报告可能包含多个墓葬，需要追踪 OCR 状态 |
| **遗址单独建表** | 同一遗址可能有多次发掘、多份报告；遗址有独立的地理坐标 |
| **材质/器型用枚举表** | 便于统计分析和 ML 分类映射 |
| **坐标同时存在 sites 和 tombs** | 遗址有大致坐标，单个墓葬可能有精确坐标 |
| **提取日志表** | 追踪 OCR pipeline 每一步的状态，便于调试和质量控制 |
| **标注/修正表** | 人工审核后可以记录修改历史，支持数据质量回溯 |

## 与现有数据的映射

### CLAUDE.md 提取字段 → 数据库字段

| CLAUDE.md 字段 | 数据库表.字段 | 备注 |
|---------------|--------------|------|
| 墓葬编号 | `tombs.tomb_number` | M1, M5, M23 |
| 年代 | `tombs.period` | 战国晚期 |
| 墓向 | `tombs.orientation` | 185° 或 南北向 |
| 墓葬形制 | `tombs.tomb_type` | 土坑竖穴墓 |
| 墓口长 | `tombs.length_m` | 统一为米 |
| 墓口宽 | `tombs.width_m` | 统一为米 |
| 墓深 | `tombs.depth_m` | 统一为米 |
| 备注 | `tombs.notes` | |
| 器物编号 | `artifacts.artifact_number` | M1:1, M1:2 |
| 器物名称 | `artifacts.name` | 陶罐 |
| 材质 | `artifacts.material_category` | 陶器 |
| 器型 | `artifacts.vessel_type` | 罐 |
| 数量 | `artifacts.quantity` | 1, 3 |
| 特征描述 | `artifacts.description` | 泥质灰陶，肩部饰弦纹 |

### 预解析 CSV → 数据库

BunnyCDN 中 10 份 CSV 的字段映射待确认（需要先读取 CSV 样本）。

## GIS 可视化支持

### 空间查询示例

```sql
-- 查找某省份的所有墓葬
SELECT * FROM tomb_overview WHERE province = '河北省';

-- 查找某朝代的所有墓葬
SELECT * FROM tomb_overview WHERE dynasty = '汉代';

-- 按材质统计器物分布
SELECT material_category, COUNT(*) FROM artifacts GROUP BY material_category;
```

### 导出为 GeoJSON

```sql
-- 导出墓葬点为 GeoJSON（用于 QGIS/Leaflet）
SELECT json_object(
    'type', 'Feature',
    'geometry', json_object(
        'type', 'Point',
        'coordinates', json_array(longitude, latitude)
    ),
    'properties', json_object(
        'tomb_number', tomb_number,
        'dynasty', dynasty,
        'tomb_type', tomb_type,
        'site_name', site_name
    )
) AS geojson
FROM tomb_overview
WHERE latitude IS NOT NULL;
```

## ML 训练数据关联

### 工作流

1. **OCR 提取器物** → `artifacts` 表
2. **图片收集** → `images` 表（来自 xunzhilu/遗址照片/报告插图）
3. **Roboflow 数据集** → `ml_datasets` 表
4. **标注映射** → `artifact_dataset_mapping` 表

### 分类体系

```
材质分类 (material_categories)
  └── 陶器/青铜器/铁器/玉石器/骨角牙器/漆木器/金银器/货币/其他

器型分类 (vessel_types)
  └── 容器类/兵器类/工具类/装饰类/车马器/乐器类/印章类
```

## 下一步

1. **验证 CSV 字段** — 读取 BunnyCDN 上 10 份 CSV，确认字段映射
2. **创建数据库** — `sqlite3 kaogu.db < schema.sql`
3. **导入预解析数据** — 编写 CSV → SQLite 导入脚本
4. **搭建 OCR pipeline** — 批量处理 199 份期刊 PDF
5. **GIS 可视化** — 使用 QGIS 或 Leaflet 展示墓葬分布

## 文件结构

```
kaogu-db/
├── schema.sql          -- 数据库 schema（本文件）
├── README.md           -- 设计说明（本文件）
├── kaogu.db            -- SQLite 数据库文件（待创建）
├── scripts/
│   ├── init_db.sh      -- 初始化数据库
│   ├── import_csv.py   -- CSV 导入脚本
│   ├── export_geojson.py -- GeoJSON 导出
│   └── ocr_pipeline.py -- OCR 批处理
└── data/
    ├── csv_samples/    -- CSV 样本
    └── exports/        -- 导出数据
```
