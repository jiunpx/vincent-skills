#!/usr/bin/env bash
# 爬取 whatmkreallysaid.com 並轉成 Markdown
# 使用方式：bash scrape_whatmk.sh

set -euo pipefail

SITE="https://whatmkreallysaid.com"
DOMAIN="whatmkreallysaid.com"
OUTPUT_DIR="./whatmk_markdown"

echo "=== 步驟 1：用 wget 鏡像整個網站 ==="
wget \
  --mirror \
  --convert-links \
  --adjust-extension \
  --page-requisites \
  --no-parent \
  --wait=1 \
  --random-wait \
  --user-agent="Mozilla/5.0 (compatible; research-bot/1.0)" \
  -e robots=off \
  "$SITE"

echo ""
echo "=== 步驟 2：將 HTML 轉成 Markdown ==="
mkdir -p "$OUTPUT_DIR"

# 優先用 pandoc，其次用 html2text，最後用 python 內建
convert_html() {
  local src="$1"
  local dst="$2"
  if command -v pandoc &>/dev/null; then
    pandoc -f html -t markdown_strict --wrap=none "$src" -o "$dst" 2>/dev/null
  elif command -v html2text &>/dev/null; then
    html2text "$src" > "$dst" 2>/dev/null
  else
    python3 -c "
from html.parser import HTMLParser
import sys

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','head'):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ('script','style','head'):
            self.skip = False
        if tag in ('p','h1','h2','h3','h4','li','br','div'):
            self.text.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)

with open(sys.argv[1], encoding='utf-8', errors='ignore') as f:
    content = f.read()
p = TextExtractor()
p.feed(content)
print(''.join(p.text))
" "$src" > "$dst" 2>/dev/null
  fi
}

export -f convert_html

find "$DOMAIN" -name "*.html" | while read -r html_file; do
  # 對應輸出路徑
  rel_path="${html_file#$DOMAIN/}"
  md_file="$OUTPUT_DIR/${rel_path%.html}.md"
  md_dir="$(dirname "$md_file")"
  mkdir -p "$md_dir"
  convert_html "$html_file" "$md_file"
  echo "  轉換：$html_file -> $md_file"
done

echo ""
echo "=== 完成！==="
echo "HTML 原始檔：./$DOMAIN/"
echo "Markdown 檔：$OUTPUT_DIR/"
echo ""
echo "頁面總數："
find "$DOMAIN" -name "*.html" | wc -l
echo ""
echo "Markdown 總數："
find "$OUTPUT_DIR" -name "*.md" | wc -l
