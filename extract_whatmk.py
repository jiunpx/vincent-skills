#!/usr/bin/env python3
"""
下載 whatmkreallysaid.com 的逐字稿 pack，轉成每集一個 Markdown 檔案。

使用方式：
  python3 extract_whatmk.py

輸出：./whatmk_transcripts/<ep_num>_<title>.md
"""

import json
import os
import re
import sys
import urllib.request

BASE_URL = "https://whatmkreallysaid.com"
OUTPUT_DIR = "./whatmk_transcripts"


def fetch_manifest():
    url = f"{BASE_URL}/pack_manifest.json"
    print(f"取得 manifest：{url}")
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def fetch_pack(version):
    """嘗試用 Accept-Encoding: br 抓 pack，讓伺服器自動壓縮。
    curl/urllib 會透明解壓。"""
    pack_url = f"{BASE_URL}/pack_{version}.json"
    print(f"下載 pack：{pack_url}  (~10MB，請稍候...)")

    req = urllib.request.Request(
        pack_url,
        headers={
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/5.0 (research)",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = r.read()
        return json.loads(data)
    except Exception as e:
        print(f"  urllib 失敗：{e}")
        print("  嘗試 brotli 解碼...")
        return fetch_pack_brotli(pack_url)


def fetch_pack_brotli(pack_url):
    try:
        import brotli
    except ImportError:
        print("  需要安裝 brotli：pip3 install brotli")
        sys.exit(1)

    req = urllib.request.Request(
        pack_url,
        headers={
            "Accept-Encoding": "br",
            "User-Agent": "Mozilla/5.0 (research)",
        },
    )
    with urllib.request.urlopen(req) as r:
        raw = r.read()

    print(f"  收到 {len(raw)/1024/1024:.1f} MB，解壓中...")
    data = brotli.decompress(raw)
    return json.loads(data)


def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip().strip(".")
    return name[:120]


def episode_to_markdown(ep):
    lines = []

    # 標題區
    num = ep.get("ep_num") or ep.get("num") or ep.get("id") or "?"
    title = ep.get("title") or ep.get("ep_title") or f"Episode {num}"
    lines.append(f"# {title}")
    lines.append("")

    # Metadata
    if ep.get("published_at") or ep.get("date"):
        lines.append(f"**日期**：{ep.get('published_at') or ep.get('date')}")
    if ep.get("description") or ep.get("summary"):
        lines.append(f"**簡介**：{ep.get('description') or ep.get('summary')}")
    lines.append("")

    # 逐字稿本文
    transcript = (
        ep.get("transcript")
        or ep.get("text")
        or ep.get("content")
        or ep.get("segments")
    )

    if isinstance(transcript, str):
        lines.append(transcript)
    elif isinstance(transcript, list):
        for seg in transcript:
            if isinstance(seg, str):
                lines.append(seg)
            elif isinstance(seg, dict):
                speaker = seg.get("speaker") or seg.get("spk") or ""
                text = seg.get("text") or seg.get("content") or ""
                ts = seg.get("start") or seg.get("timestamp") or ""
                if speaker:
                    lines.append(f"**{speaker}**：{text}")
                else:
                    lines.append(text)
    else:
        # fallback：直接序列化未知結構
        lines.append(json.dumps(ep, ensure_ascii=False, indent=2))

    return "\n".join(lines)


def main():
    manifest = fetch_manifest()
    version = manifest["version"]
    ep_count = manifest.get("episode_count", "?")
    print(f"版本：{version}，共 {ep_count} 集")

    pack = fetch_pack(version)

    # pack 可能是 list 或 dict，找出 episodes
    if isinstance(pack, list):
        episodes = pack
    elif isinstance(pack, dict):
        episodes = (
            pack.get("episodes")
            or pack.get("transcripts")
            or pack.get("items")
            or list(pack.values())
        )
    else:
        print(f"未預期的 pack 格式：{type(pack)}")
        print(json.dumps(pack, ensure_ascii=False)[:500])
        sys.exit(1)

    print(f"解析到 {len(episodes)} 集，開始輸出...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for ep in episodes:
        if not isinstance(ep, dict):
            continue
        num = ep.get("ep_num") or ep.get("num") or ep.get("id") or "0"
        title = ep.get("title") or ep.get("ep_title") or f"ep_{num}"
        filename = f"{str(num).zfill(4)}_{sanitize_filename(title)}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(episode_to_markdown(ep))

    total = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")])
    print(f"\n完成！共輸出 {total} 個 .md 檔案到：{OUTPUT_DIR}/")

    # 顯示第一集結構以供確認
    if episodes:
        print("\n第一集的 key 結構：")
        first = episodes[0]
        if isinstance(first, dict):
            for k, v in first.items():
                preview = str(v)[:80] if not isinstance(v, (list, dict)) else f"[{type(v).__name__}, len={len(v)}]"
                print(f"  {k}: {preview}")


if __name__ == "__main__":
    main()
