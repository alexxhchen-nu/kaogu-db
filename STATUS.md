# 考古墓葬数据库 - 项目状态

**更新时间**: 2026-07-11

## 已完成

- ✅ 设计并实现 SQLite schema（11 个表 + 3 个视图）
- ✅ 创建示例数据（满城汉墓 M1/M2）
- ✅ 验证 GIS 查询和 GeoJSON 导出
- ✅ 编写设计说明文档
- ✅ VPS 部署 schema（`vps-llm-kaogu/kaogu.db`，12 张表）
- ✅ 安装 PyMuPDF 依赖

## 文件结构

### 本地 (Mac)
```
/Users/xiaohanchen/projects/kaogu-db/
├── schema.sql              -- 数据库 schema
├── schema_vps.sql          -- VPS 版本
├── README.md               -- 设计说明
├── STATUS.md               -- 本文件
├── kaogu.db                -- 本地 SQLite 数据库
├── scripts/
│   ├── init_db.sh          -- 初始化脚本
│   └── ocr_pipeline.py     -- OCR 管线（主要）
└── notebooks/
    └── ocr_pipeline.ipynb  -- Jupyter notebook
```

### VPS (ml)
```
/root/xiaohanchen/projects/vps-llm-kaogu/
├── kaogu.db                -- 生产数据库
├── schema.sql              -- Schema
├── scripts/
│   ├── ocr_pipeline.py     -- OCR 管线
│   ├── pdf_ocr_extract.py  -- 旧版 OCR
│   └── ...                 -- 其他脚本
├── notebooks/
│   ├── ocr_pipeline.ipynb  -- 新 notebook
│   └── ...                 -- 其他 notebooks
└── data/
    ├── pdfs/               -- 13 个丁种报告 PDF
    └── extracted/          -- OCR 提取结果
```

## 核心表

| 表名 | 用途 | 本地记录数 | VPS 记录数 |
|------|------|--------|--------|
| reports | 考古报告来源 | 1 | 1 |
| sites | 遗址/发掘地点 | 1 | 0 |
| tombs | 墓葬信息 | 2 | 9 |
| artifacts | 随葬器物 | 5 | 26 |
| material_categories | 材质分类枚举 | 9 | 9 |
| vessel_types | 器型分类枚举 | 47 | 47 |
| images | 图片资源 | 0 | 0 |
| ml_datasets | ML 数据集 | 0 | 0 |
| artifact_dataset_mapping | 器物-数据集映射 | 0 | 0 |
| extraction_logs | OCR 提取日志 | 0 | 1 |
| annotations | 人工标注/修正 | 0 | 0 |

## 视图

- `tomb_overview` — 墓葬概览（用于 GIS 可视化）
- `artifact_stats` — 器物统计（用于分析）
- `report_progress` — 报告处理进度

## 当前进度：Track B — OCR 管线

### Phase 1：VPS 数据库部署 ✅
- Schema 部署到 VPS `/root/xiaohanchen/projects/vps-llm-kaogu/kaogu.db`
- PyMuPDF 已安装

### Phase 2：OCR 管线改进 ✅
- `scripts/ocr_pipeline.py` 已完成：
  - 更精确的墓葬编号正则（M1、一号墓、第1号墓）
  - 直接写入 SQLite 数据库
  - 支持批量处理多个 PDF
  - 提取完整字段（朝代、墓向、形制、尺寸）
  - 测试结果：50 页 → 9 座墓葬, 26 件器物
- Notebook: `notebooks/ocr_pipeline.ipynb`

### Phase 3：R2 期刊 OCR 🔄 运行中
- 143 个期刊 PDF 已从 R2 下载到 VPS（文物 117 + 文物1972 1 + 考古学报 25）
- tmux `r2-ocr` 正在处理
- 当前进度：3 报告, 10 墓葬, 27 器物

#### 使用方法
```bash
# 处理单个 PDF
python scripts/ocr_pipeline.py "data/pdfs/满城汉墓_上册.pdf"

# 批量处理目录
python scripts/ocr_pipeline.py --batch data/pdfs/

# 限制页数测试
python scripts/ocr_pipeline.py "data/pdfs/满城汉墓_上册.pdf" --max-pages 50

# 查看数据库
sqlite3 kaogu.db "SELECT * FROM tomb_overview;"
```

### Phase 3：批量处理 ⬜
- VPS 上 13 个丁种报告 PDF（723 MB）
- R2 上 199 个期刊 PDF（需下载到 VPS）

## 当前进度：Track A — CSV 导入 ✅

### 已完成
- ✅ 获取 BunnyCDN 凭证（gopass `api/env/BUNNY_*`）
- ✅ 创建 CSV 导入脚本（`scripts/import_csv.py`）
- ✅ 导入 10 个预解析 CSV 文件
- ✅ 数据验证通过

### 导入统计
| 来源 | 墓葬 | 器物 |
|------|------|------|
| 河北省考古文集（1） | 91 | 139 |
| 河北省考古文集（2） | 97 | 506 |
| 河北省考古文集（3） | 166 | 197 |
| 南水北调（2） | 131 | 701 |
| 南水北调（3） | 139 | 244 |
| 南水北调（5） | 23 | 11 |
| 南水北调（6） | 57 | 176 |
| 南水北调（8） | 49 | 240 |
| 南水北调（10） | 46 | 36 |
| 南水北调（11） | 99 | 41 |
| **总计** | **898** | **2,291** |

### 数据分布
- **朝代**: 秦至西汉(126), 清代(121), 东汉(100), 西汉(100), 汉代(51), 战国中晚期(45), 晚商(41), 唐代(33)
- **墓葬形制**: 长方形竖穴土坑墓(207), 砖室墓(76), 土坑竖穴墓(72), 土坑墓(71)
- **器物材质**: 陶器(1212), 青铜器(215), 瓷器(75), 货币(68), 铁器(57), 玉石器(45)

## 下一步

### Track B（OCR 管线）
1. **处理 VPS 上的 13 个 PDF** — 运行批量 OCR
2. **优化提取精度** — 改进墓葬编号标准化、器物名称提取
3. **处理 R2 上的 199 个期刊 PDF** — 下载到 VPS 并处理

### Track A（CSV + GIS）✅
1. ✅ **获取 BunnyCDN 凭证** — 已从 gopass 获取
2. ✅ **编写 CSV 导入脚本** — `scripts/import_csv.py`
3. ✅ **导入 10 个 CSV** — 898 座墓葬, 2,291 件器物
4. ✅ **GIS 可视化** — Leaflet 地图已生成，64 个站点，633 座墓葬
5. ✅ **GitHub 仓库** — `alexxhchen-nu/kaogu-db`

## 使用示例

```bash
# 初始化数据库
sqlite3 kaogu.db < schema.sql

# 查询某朝代墓葬
sqlite3 kaogu.db "SELECT * FROM tomb_overview WHERE dynasty = '西汉';"

# 导出 GeoJSON
sqlite3 kaogu.db "SELECT json_object('type', 'Feature', ...) FROM tomb_overview;"

# 统计器物分布
sqlite3 kaogu.db "SELECT * FROM artifact_stats;"
```
