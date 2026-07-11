#!/bin/bash
# 初始化考古墓葬数据库
set -e

DB_PATH="${1:-../kaogu.db}"
SCHEMA_PATH="$(dirname "$0")/../schema.sql"

echo "正在创建数据库: $DB_PATH"
sqlite3 "$DB_PATH" < "$SCHEMA_PATH"

echo "数据库初始化完成！"
echo "表结构:"
sqlite3 "$DB_PATH" ".tables"
echo ""
echo "记录数:"
sqlite3 "$DB_PATH" "SELECT 'reports: ' || COUNT(*) FROM reports;"
sqlite3 "$DB_PATH" "SELECT 'sites: ' || COUNT(*) FROM sites;"
sqlite3 "$DB_PATH" "SELECT 'tombs: ' || COUNT(*) FROM tombs;"
sqlite3 "$DB_PATH" "SELECT 'artifacts: ' || COUNT(*) FROM artifacts;"
sqlite3 "$DB_PATH" "SELECT 'images: ' || COUNT(*) FROM images;"
