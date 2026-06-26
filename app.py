#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
透過検証ツール - Web版 (Streamlit)
PSD / PNG ファイルの透過チャンネル（alpha > 0 のピクセル）を検証します。
"""

import io
import streamlit as st
import numpy as np
from PIL import Image, ImageDraw, ImageOps

# ── ページ設定 ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="透過検証ツール",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── カスタム CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F2F2F7; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; }
    .result-label-ok {
        text-align: center;
        color: #30D158;
        font-size: 11px;
        line-height: 1.4;
        margin-top: 4px;
    }
    .result-label-ng {
        text-align: center;
        color: #FF453A;
        font-size: 11px;
        line-height: 1.4;
        margin-top: 4px;
    }
    .summary-ok  { color: #30D158; font-weight: bold; }
    .summary-ng  { color: #FF453A; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── ユーティリティ関数 ─────────────────────────────────────────────────

def make_checker_thumb(img: Image.Image, size: int) -> Image.Image:
    """numpy ベクトル演算でチェッカーボード背景のサムネイルを高速生成"""
    cell = 10
    cw, ch = img.size
    if cw == 0 or ch == 0:
        return Image.new("RGB", (size, size), (100, 100, 100))
    yi = np.arange(ch) // cell
    xi = np.arange(cw) // cell
    checker = ((yi[:, None] + xi[None, :]) % 2).astype(np.uint8)
    gray = np.where(checker == 0, 200, 160).astype(np.uint8)
    bg_arr = np.stack(
        [gray, gray, gray, np.full((ch, cw), 255, dtype=np.uint8)],
        axis=-1,
    )
    bg = Image.fromarray(bg_arr, "RGBA")
    bg.paste(img, (0, 0), img)
    bg.thumbnail((size, size), Image.LANCZOS)
    return bg


def find_bboxes(mask: np.ndarray) -> list:
    """不透明ピクセルの連続領域の bbox を返す"""
    try:
        from scipy.ndimage import label as nd_label
        labeled, n = nd_label(mask)
        bboxes = []
        for k in range(1, n + 1):
            ys, xs = np.where(labeled == k)
            bboxes.append((int(xs.min()), int(ys.min()),
                           int(xs.max()), int(ys.max())))
        return bboxes
    except ImportError:
        ys, xs = np.where(mask)
        return [(int(xs.min()), int(ys.min()),
                 int(xs.max()), int(ys.max()))]


def draw_bboxes(img: Image.Image, bboxes: list) -> Image.Image:
    """不透明領域に赤矩形をハイライト表示"""
    out  = img.copy()
    draw = ImageDraw.Draw(out)
    bw   = max(2, img.width // 200 + 1)
    for (x0, y0, x1, y1) in bboxes:
        draw.rectangle(
            [max(0, x0 - bw),            max(0, y0 - bw),
             min(img.width - 1, x1 + bw), min(img.height - 1, y1 + bw)],
            outline=(255, 0, 0, 255), width=bw,
        )
    return out


def analyze_image(img: Image.Image) -> dict:
    """アルファチャンネルを解析して結果辞書を返す"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr   = np.array(img)
    alpha = arr[:, :, 3]
    mask  = alpha > 0

    if not np.any(mask):
        return {"has_garbage": False, "pixel_count": 0, "bboxes": [], "img": img}

    pixel_count = int(np.sum(mask))
    bboxes      = find_bboxes(mask)
    return {
        "has_garbage": True,
        "pixel_count": pixel_count,
        "bboxes":      bboxes,
        "img":         draw_bboxes(img, bboxes),
    }


def framed_thumb(img: Image.Image, has_garbage: bool, border: int = 6) -> Image.Image:
    """合否ボーダー付きサムネイルを RGB で返す"""
    color = (180, 30, 30) if has_garbage else (30, 160, 60)
    return ImageOps.expand(img.convert("RGB"), border=border, fill=color)


def show_results(results: list, cols_count: int):
    """結果をグリッド表示する"""
    if not results:
        st.warning("処理できた画像がありませんでした。")
        return

    # ── サマリー ──────────────────────────────────────────────────
    gc = sum(1 for r in results if r["has_garbage"])
    ok = len(results) - gc

    m1, m2, m3 = st.columns(3)
    m1.metric("合計",       f"{len(results)} 件")
    m2.metric("✅ クリーン", f"{ok} 件")
    m3.metric("❌ ゴミあり", f"{gc} 件")
    st.divider()

    # ── グリッド ──────────────────────────────────────────────────
    cols = st.columns(cols_count)
    for i, res in enumerate(results):
        with cols[i % cols_count]:
            thumb = framed_thumb(res["thumb"], res["has_garbage"])
            st.image(thumb, use_container_width=True)
            if res["has_garbage"]:
                st.markdown(
                    f'<div class="result-label-ng">✗ {res["name"]}<br>'
                    f'{res["pixel_count"]:,} px &nbsp;|&nbsp; {len(res["bboxes"])} 領域</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="result-label-ok">✓ {res["name"]}<br>クリーン</div>',
                    unsafe_allow_html=True,
                )


# ── サイドバー ─────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🔍 透過検証ツール")
    st.caption("alpha > 0 のピクセルをゴミとして検出します")
    st.divider()

    mode = st.radio("モード", ["PNG ファイル", "PSD レイヤー"])
    st.divider()

    thumb_size = st.slider("サムネイルサイズ (px)", 80, 400, 180, 10)
    cols_count = st.slider("列数", 1, 8, 4)
    st.divider()

    st.caption("**凡例**")
    st.markdown("🟥 ゴミあり（不透明ピクセル検出）")
    st.markdown("🟩 クリーン（完全透過）")


# ── メインエリア ───────────────────────────────────────────────────────

if mode == "PNG ファイル":
    st.header("PNG 透過検証")
    st.caption("フォルダから PNG ファイルを複数まとめてドラッグ＆ドロップできます")

    uploaded_files = st.file_uploader(
        "PNG ファイルをドラッグ＆ドロップ（複数可）",
        type=["png"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} 件のファイルが読み込まれています")

        if st.button("🔍 検証実行", type="primary"):
            results  = []
            progress = st.progress(0, text="処理中...")

            for i, f in enumerate(uploaded_files):
                progress.progress(
                    (i + 1) / len(uploaded_files),
                    text=f"[{i+1}/{len(uploaded_files)}] {f.name}",
                )
                try:
                    img = Image.open(f)
                    res = analyze_image(img)
                    res["name"]  = f.name
                    res["thumb"] = make_checker_thumb(res["img"], thumb_size)
                    results.append(res)
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")

            progress.empty()
            show_results(results, cols_count)

else:  # PSD モード
    st.header("PSD レイヤー透過検証")
    st.caption("PSD の末端レイヤーを1枚ずつ個別に検証します")

    uploaded_file = st.file_uploader(
        "PSD ファイルをドラッグ＆ドロップ",
        type=["psd", "psb"],
        accept_multiple_files=False,
    )

    if uploaded_file:
        st.info(f"ファイル: {uploaded_file.name}  ({uploaded_file.size / 1024 / 1024:.1f} MB)")

        if st.button("🔍 検証実行", type="primary"):
            try:
                from psd_tools import PSDImage
            except ImportError:
                st.error("psd-tools がインストールされていません。")
                st.stop()

            with st.spinner("PSD を読み込み中..."):
                psd = PSDImage.open(io.BytesIO(uploaded_file.read()))

            st.info(f"キャンバス: {psd.width} × {psd.height} px")

            # 末端レイヤーを再帰的に収集
            leaf_layers: list = []

            def _collect(layer, prefix=""):
                if layer.is_group():
                    for child in layer:
                        _collect(child, prefix + layer.name + "/")
                else:
                    leaf_layers.append((layer, prefix))

            for layer in psd:
                _collect(layer)

            if not leaf_layers:
                st.warning("末端レイヤーが見つかりませんでした。")
                st.stop()

            results  = []
            progress = st.progress(0, text="処理中...")

            for i, (layer, prefix) in enumerate(leaf_layers):
                progress.progress(
                    (i + 1) / len(leaf_layers),
                    text=f"[{i+1}/{len(leaf_layers)}] {layer.name}",
                )
                label = prefix + layer.name
                try:
                    img = layer.topil()
                    if img is None:
                        continue
                    res = analyze_image(img)
                    res["name"]  = label
                    res["thumb"] = make_checker_thumb(res["img"], thumb_size)
                    results.append(res)
                except Exception as e:
                    st.warning(f"⚠️ {label}: {e}")

            progress.empty()
            show_results(results, cols_count)
