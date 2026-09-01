<div align="center">

<img src="docs/assets/banner.svg" alt="Morpho - Structural Color Simulator" width="100%" />

</div>

## クイックスタート

以下がインストールされている必要があります。

- [uv](https://docs.astral.sh/uv/)
- Node.js
- C++ コンパイラ(RCWA ソルバー [S4](https://web.stanford.edu/group/fan/S4/) のビルドに使用)

```bash
git clone https://github.com/sotaro711/Morpho.git
cd Morpho
(cd backend && uv sync)      # 初回は S4 のビルドが走ります
(cd frontend && npm install)
./dev.sh                     # バックエンド :8000 / フロントエンド :3000
```

http://localhost:3000 でシミュレーターが開きます。API ドキュメントは http://localhost:8000/docs で確認できます。

### Docker で起動する場合

```bash
docker build -t morpho .
docker run --rm -p 8080:8080 morpho
```

http://localhost:8080 で開きます。
