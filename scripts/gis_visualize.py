"""
GIS 可视化 — 从 SQLite 生成 Leaflet 地图
用法: python scripts/gis_visualize.py [--db kaogu.db] [--output map.html]
"""
import sqlite3, json, argparse
from pathlib import Path

# 已知地名 → 坐标（河北省常见考古地点）
KNOWN_COORDS = {
    # 河北省
    "满城": (38.95, 115.32),
    "保定": (38.87, 115.46),
    "石家庄": (38.04, 114.51),
    "邢台": (37.07, 114.50),
    "邯郸": (36.60, 114.49),
    "涿州": (39.49, 115.97),
    "鹿泉": (38.09, 114.31),
    "武邑": (37.80, 115.89),
    "柏乡": (37.49, 114.69),
    "献县": (38.17, 116.10),
    "深州": (38.00, 115.56),
    "博野": (38.46, 115.46),
    "内邱": (37.29, 114.51),
    "涉县": (36.58, 113.69),
    "景县": (37.69, 116.27),
    "故城": (37.35, 115.97),
    "滦平": (40.94, 117.33),
    "固安": (39.44, 116.30),
    "蔚县": (39.84, 114.57),
    "徐水": (39.02, 115.65),
    "易县": (39.35, 115.50),
    "磁县": (36.37, 114.38),
    "曲阳": (38.62, 114.70),
    "正定": (38.15, 114.57),
    "赵县": (37.76, 114.78),
    "元氏": (37.76, 114.52),
    "廊坊": (39.52, 116.70),
    "安次": (39.52, 116.69),
    "大城": (38.70, 116.64),
    "文安": (38.87, 116.46),
    "永清": (39.32, 116.50),
    "香河": (39.76, 117.01),
    "三河": (39.98, 117.08),
    "青龙": (40.41, 118.95),
    "昌黎": (39.71, 119.15),
    "抚宁": (39.88, 119.23),
    "卢龙": (39.89, 118.87),
    "迁安": (40.00, 118.70),
    "迁西": (40.14, 118.32),
    "遵化": (40.19, 117.96),
    "玉田": (39.90, 117.74),
    "丰润": (39.83, 118.16),
    "丰南": (39.57, 118.11),
    "滦南": (39.50, 118.68),
    "乐亭": (39.43, 118.90),
    "唐海": (39.28, 118.46),
    "承德": (40.97, 117.93),
    "兴隆": (40.42, 117.50),
    "平泉": (40.98, 118.70),
    "隆化": (41.32, 117.73),
    "围场": (41.94, 117.76),
    "丰宁": (41.21, 116.65),
    "宽城": (40.61, 118.49),
    "张家口": (40.77, 114.88),
    "宣化": (40.59, 115.05),
    "怀来": (40.41, 115.52),
    "涿鹿": (40.38, 115.22),
    "阳原": (40.11, 114.16),
    "怀安": (40.67, 114.39),
    "万全": (40.77, 114.73),
    "崇礼": (40.97, 115.28),
    "赤城": (40.91, 115.83),
    "沽源": (41.67, 115.69),
    "康保": (41.85, 114.61),
    "尚义": (41.08, 113.97),
    "张北": (41.16, 114.72),
    # 南水北调沿线
    "土城": (39.50, 115.90),
    "讲武城": (36.35, 114.35),
    "双庙": (36.36, 114.36),
    "官庄": (38.10, 115.50),
    "张夺": (37.80, 114.70),
    "南吴会": (37.50, 114.60),
    "西龙贵": (37.55, 114.55),
    "殷村": (37.52, 114.53),
    "东黑山": (39.02, 115.65),
    "后太保": (38.05, 114.52),
    "岳村铺": (38.03, 114.48),
    "肖家营": (38.06, 114.50),
    "刘疃": (37.82, 115.90),
    "龙店": (37.81, 115.88),
    "刘陀店": (38.47, 115.47),
    "小驿头": (37.30, 114.52),
    "高庄": (38.10, 114.32),
    "泽丰": (37.07, 114.51),
    "下博": (38.01, 115.57),
    "万村": (38.18, 116.11),
    "大伍龙": (39.53, 116.71),
    "公主府": (39.45, 116.31),
    "和平丽景": (39.52, 116.70),
    "紫园": (38.87, 115.47),
    # 燕下都
    "燕下都": (39.35, 115.50),
    # 湾漳营
    "滏阳营": (36.37, 114.38),
    "湾漳营": (36.37, 114.38),
    "东窑头": (36.38, 114.39),
    "槐树屯": (36.39, 114.40),
    # 其他
    "中角": (37.82, 115.89),
    "南海山": (38.08, 114.32),
    "北新城": (38.10, 114.30),
    "东沟": (39.50, 115.90),
    "白桦沟": (39.51, 115.91),
    "陵上寺": (38.18, 116.11),
    "龙店": (37.81, 115.88),
    "刘疃": (37.82, 115.90),
    "刘陀店": (38.47, 115.47),
    "小驿头": (37.30, 114.52),
    "高庄": (38.10, 114.32),
    "泽丰": (37.07, 114.51),
    "下博": (38.01, 115.57),
    "万村": (38.18, 116.11),
    "大伍龙": (39.53, 116.71),
    "公主府": (39.45, 116.31),
    "和平丽景": (39.52, 116.70),
    "紫园": (38.87, 115.47),
    "肖家营": (38.06, 114.50),
    "岳村铺": (38.03, 114.48),
}

def geocode_site(name, province=None, city=None):
    """根据站点名称和已知坐标表进行地理编码"""
    # 精确匹配
    for key, coords in KNOWN_COORDS.items():
        if key in name:
            return coords
    
    # 根据省份猜测
    if province == "河北":
        return (38.0, 115.0)  # 河北省中心
    if province == "河南":
        return (34.0, 113.5)
    if province == "陕西":
        return (34.3, 108.9)
    if province == "山西":
        return (37.9, 112.6)
    
    return None

def get_site_tomb_counts(db_path):
    """获取每个站点的墓葬数量"""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT s.id, s.name, s.province, s.city, s.latitude, s.longitude,
               COUNT(t.id) as tomb_count,
               GROUP_CONCAT(DISTINCT t.dynasty) as dynasties
        FROM sites s
        LEFT JOIN tombs t ON t.site_id = s.id
        GROUP BY s.id
    """).fetchall()
    conn.close()
    return rows

def generate_map(db_path, output_path):
    """生成 Leaflet HTML 地图"""
    sites = get_site_tomb_counts(db_path)
    
    # 准备 GeoJSON 数据
    features = []
    geocoded_count = 0
    
    for site_id, name, province, city, lat, lon, tomb_count, dynasties in sites:
        # 如果没有坐标，尝试地理编码
        if lat is None or lon is None:
            coords = geocode_site(name, province, city)
            if coords:
                lat, lon = coords
                geocoded_count += 1
                # 更新数据库
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE sites SET latitude = ?, longitude = ? WHERE id = ?", (lat, lon, site_id))
                conn.commit()
                conn.close()
        
        if lat and lon:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "id": site_id,
                    "name": name,
                    "province": province or "",
                    "city": city or "",
                    "tomb_count": tomb_count,
                    "dynasties": dynasties or ""
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # 生成 HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>考古墓葬分布图</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Microsoft YaHei', sans-serif; }}
        #map {{ width: 100%; height: 100vh; }}
        .info-panel {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            max-width: 300px;
        }}
        .info-panel h3 {{ margin: 0 0 10px 0; color: #333; }}
        .info-panel .stat {{ margin: 5px 0; font-size: 14px; }}
        .marker-label {{
            background: rgba(255,255,255,0.9);
            border: 1px solid #666;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 12px;
            white-space: nowrap;
        }}
        .legend {{
            position: absolute;
            bottom: 30px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="info-panel">
        <h3>考古墓葬分布图</h3>
        <div class="stat">总站点数: <strong>{len(features)}</strong></div>
        <div class="stat">墓葬总数: <strong>{sum(f['properties']['tomb_count'] for f in features)}</strong></div>
        <div class="stat">地理编码: <strong>{geocoded_count}</strong> 个站点</div>
        <hr>
        <div class="stat" style="font-size:12px; color:#666;">
            点击标记查看详情 | 滚轮缩放 | 拖拽平移
        </div>
    </div>
    <div class="legend">
        <div style="font-weight:bold; margin-bottom:8px;">墓葬数量</div>
        <div class="legend-item">
            <div class="legend-dot" style="background:#3388ff; width:10px; height:10px;"></div>
            <span>1-5 座</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background:#ff6b35; width:14px; height:14px;"></div>
            <span>6-20 座</span>
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background:#ff1744; width:18px; height:18px;"></div>
            <span>21+ 座</span>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([38.5, 115.5], 7);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18
        }}).addTo(map);
        
        var data = {json.dumps(geojson, ensure_ascii=False)};
        
        function getColor(count) {{
            if (count > 20) return '#ff1744';
            if (count > 5) return '#ff6b35';
            return '#3388ff';
        }}
        
        function getSize(count) {{
            if (count > 20) return 14;
            if (count > 5) return 10;
            return 7;
        }}
        
        L.geoJSON(data, {{
            pointToLayer: function(feature, latlng) {{
                var count = feature.properties.tomb_count;
                return L.circleMarker(latlng, {{
                    radius: getSize(count),
                    fillColor: getColor(count),
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }});
            }},
            onEachFeature: function(feature, layer) {{
                var p = feature.properties;
                var popup = '<div style="min-width:200px;">' +
                    '<h4 style="margin:0 0 8px 0;">' + p.name + '</h4>' +
                    '<p style="margin:4px 0;"><b>省份:</b> ' + (p.province || '未知') + '</p>' +
                    '<p style="margin:4px 0;"><b>城市:</b> ' + (p.city || '未知') + '</p>' +
                    '<p style="margin:4px 0;"><b>墓葬数:</b> ' + p.tomb_count + '</p>' +
                    '<p style="margin:4px 0;"><b>朝代:</b> ' + (p.dynasties || '未知') + '</p>' +
                    '</div>';
                layer.bindPopup(popup);
                
                if (p.tomb_count > 10) {{
                    layer.bindTooltip(p.name + ' (' + p.tomb_count + ')', {{
                        permanent: true,
                        direction: 'right',
                        className: 'marker-label'
                    }});
                }}
            }}
        }}).addTo(map);
        
        // 自动缩放到数据范围
        if (data.features.length > 0) {{
            var bounds = L.geoJSON(data).getBounds();
            map.fitBounds(bounds.pad(0.1));
        }}
    </script>
</body>
</html>"""
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    print(f"✅ 地图已生成: {output}")
    print(f"   站点数: {len(features)}")
    print(f"   墓葬总数: {sum(f['properties']['tomb_count'] for f in features)}")
    print(f"   地理编码: {geocoded_count} 个")

def main():
    parser = argparse.ArgumentParser(description="GIS 可视化")
    parser.add_argument("--db", default="kaogu.db", help="数据库路径")
    parser.add_argument("--output", default="map.html", help="输出 HTML 路径")
    args = parser.parse_args()
    
    generate_map(args.db, args.output)

if __name__ == "__main__":
    main()
