# 透過検証ツール

PSD レイヤー / PNG ファイルの透過チャンネル（alpha > 0 のピクセル）をブラウザ上で検証するツールです。

## 機能

- **PNG モード**: 複数の PNG ファイルをドラッグ＆ドロップして一括検証
- **PSD モード**: PSD の末端レイヤーを個別に検証
- チェッカーボード背景でアルファを可視化
- 不透明ピクセルを赤矩形でハイライト
- 🟥 ゴミあり / 🟩 クリーン でグリッド表示

## Streamlit Cloud へのデプロイ手順

1. このリポジトリを GitHub にプッシュ
2. [share.streamlit.io](https://share.streamlit.io) にログイン
3. **"New app"** → リポジトリ・ブランチ・`app.py` を選択
4. **Advanced settings** → Python version: **3.12** を選択
5. **Deploy** をクリック

## ローカルで動かす場合

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 使用パッケージ

| パッケージ | バージョン | 用途 |
|---|---|---|
| streamlit | >=1.58.0 | Web UI |
| psd-tools | >=1.17.0 | PSD 解析 |
| Pillow | >=12.0.0 | 画像処理 |
| numpy | >=2.0.0 | アルファ解析 |
| scipy | >=1.18.0 | 連続領域検出 |
