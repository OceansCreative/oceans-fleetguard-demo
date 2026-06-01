<div align="center">

# 🛰️ FleetGuard

**An open-source, Traccar-powered fleet tracking & anti-theft dashboard.**

A reference implementation for real-time GPS vehicle tracking, geofencing, and
theft detection — built with Next.js, FastAPI, and a fully testable pure-function
detection core.

[![CI](https://github.com/OceansCreative/oceans-fleetguard-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/OceansCreative/oceans-fleetguard-demo/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-pending-lightgrey)](https://github.com/OceansCreative/oceans-fleetguard-demo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

[English](#english) · [日本語](#日本語)

</div>

---

## English

### What is FleetGuard?

FleetGuard is a generic, production-style dashboard that sits in front of a
[Traccar](https://www.traccar.org/) GPS server. It normalizes Traccar's REST
and WebSocket APIs into a clean contract, layers **anti-theft detection** on
top, and presents everything in a live map dashboard.

It ships with a **mock mode** so you can run the entire experience — vehicles
moving in real time, alerts firing — without any GPS hardware or Traccar
instance.

> ℹ️ This repository is a **generic reference implementation**. It contains
> mock data only and no client-specific customization.

### Features

- 🗺️ **Live map** — vehicle positions stream in over WebSocket.
- 🚗 **Vehicle list & detail panel** — status, speed, ignition, last update.
- 🚨 **Anti-theft detection** — implemented as pure functions for easy testing:
  - Geofence breach
  - Movement outside business / off-hours
  - Movement while ignition is OFF
  - Abnormal speed / heading
- 🔔 **Alert UI** — surfaced in the dashboard the moment a rule trips.
- 🧪 **Mock mode** — simulated vehicles around Matsue / Yasugi / Yonago, toggled
  by an environment variable.

### Architecture

```mermaid
flowchart LR
    subgraph Browser
        FE["frontend/<br/>Next.js 15 (App Router)<br/>TypeScript · Map · Alert UI"]
    end
    subgraph Server
        BE["backend/<br/>FastAPI relay + normalization<br/>theft-detection (pure functions)"]
    end
    subgraph Upstream
        TR["Traccar<br/>REST / WebSocket"]
        PG[("PostgreSQL")]
        MOCK["Mock generator<br/>(MOCK_MODE=true)"]
    end

    FE <-- "REST + WebSocket" --> BE
    BE <-- "REST / WS" --> TR
    BE -. "when MOCK_MODE" .-> MOCK
    TR --- PG
```

| Layer        | Stack                                                        |
| ------------ | ------------------------------------------------------------ |
| `frontend/`  | Next.js 15 (App Router), TypeScript (strict), Leaflet/MapLibre |
| `backend/`   | FastAPI (Python 3.12), pure-function theft detection         |
| `infra/`     | docker-compose: Traccar + PostgreSQL + backend + frontend    |

### Quick start

```bash
# 1. Clone and configure
git clone https://github.com/OceansCreative/oceans-fleetguard-demo.git
cd oceans-fleetguard-demo
cp .env.example .env        # mock mode is enabled by default

# 2. Bring up the full stack (Traccar + Postgres + backend + frontend)
docker compose -f infra/docker-compose.yml up

# 3. Open the dashboard
open http://localhost:3000
```

With `MOCK_MODE=true` (the default) you'll immediately see simulated vehicles
moving around the Matsue area — no Traccar account required.

### Project status

🚧 **Early development.** The roadmap is delivered in small, reviewed pull
requests. See the [issues](https://github.com/OceansCreative/oceans-fleetguard-demo/issues)
for what's planned and in progress.

### Screenshots

The live dashboard — fleet list, real-time map with the selected vehicle's
geofence, and the anti-theft alert feed. A light / dark / aerial basemap
switcher is built in.

| Light | Dark |
| --- | --- |
| ![FleetGuard dashboard, light basemap](./docs/img/dashboard-light.png) | ![FleetGuard dashboard, dark basemap](./docs/img/dashboard-dark.png) |

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for
the branch / PR / review workflow and local development setup.

### License

[MIT](./LICENSE)

---

## 日本語

### FleetGuard とは

FleetGuard は、[Traccar](https://www.traccar.org/) GPS サーバーの前段に置く
汎用的な車両追跡・**盗難対策**ダッシュボードの参照実装です。Traccar の REST /
WebSocket API を整形して扱いやすい形に正規化し、その上に盗難検知ロジックを重ね、
ライブ地図ダッシュボードとして提供します。

**mock モード**を同梱しているため、GPS 機器や Traccar インスタンスが無くても、
車両がリアルタイムに動き・アラートが発火する一連の体験をそのまま動かせます。

> ℹ️ 本リポジトリは**汎用リファレンス実装**です。mock データのみを含み、特定
> クライアント固有のカスタマイズは含みません。

### 機能

- 🗺️ **ライブ地図** — WebSocket で車両位置をストリーミング更新
- 🚗 **車両一覧・詳細パネル** — 状態 / 速度 / イグニッション / 最終更新
- 🚨 **盗難検知** — テスト容易な pure function として実装：
  - ジオフェンス逸脱
  - 営業 / 在宅時間外の移動
  - イグニッション OFF 中の移動
  - 速度・進路の異常
- 🔔 **アラート UI** — 判定が成立した瞬間にダッシュボードへ表示
- 🧪 **mock モード** — 松江・安来・米子周辺で動く擬似車両を環境変数で切替

### アーキテクチャ

上記の図を参照してください（`frontend/` ↔ `backend/` ↔ Traccar）。

| レイヤ       | 技術スタック                                                   |
| ------------ | -------------------------------------------------------------- |
| `frontend/`  | Next.js 15 (App Router) / TypeScript(strict) / Leaflet・MapLibre |
| `backend/`   | FastAPI (Python 3.12) / pure function による盗難検知           |
| `infra/`     | docker-compose: Traccar + PostgreSQL + backend + frontend      |

### クイックスタート

```bash
cp .env.example .env        # 既定で mock モードが有効
docker compose -f infra/docker-compose.yml up
# http://localhost:3000 を開く
```

### ステータス

🚧 **初期開発中**。ロードマップは小さくレビュー済みの PR 単位で進めます。

### スクリーンショット

ライブダッシュボード（車両一覧・選択車両のジオフェンス付きリアルタイム地図・
盗難アラート）。地図は明 / 暗 / 航空写真の切替に対応しています。

| ライト | ダーク |
| --- | --- |
| ![FleetGuard ダッシュボード（ライト基図）](./docs/img/dashboard-light.png) | ![FleetGuard ダッシュボード（ダーク基図）](./docs/img/dashboard-dark.png) |

### コントリビュート

[CONTRIBUTING.md](./CONTRIBUTING.md) を参照してください。

### ライセンス

[MIT](./LICENSE)

---

## Maintainer setup TODO

> These are one-time manual steps to be performed in the GitHub UI (not done
> automatically by code).

- [ ] **About → Description**: e.g. _"Open-source Traccar-powered fleet
      tracking & anti-theft dashboard (Next.js + FastAPI)."_
- [ ] **About → Topics**: `traccar`, `gps-tracking`, `fleet-management`,
      `nextjs`, `fastapi`, `typescript`, `python`
- [ ] **Branch protection** on the default branch: require PR review + green CI.
- [ ] **Secrets**: register Traccar credentials and any deploy tokens (never
      commit them — use `.env` locally / GitHub Secrets in CI).
- [ ] **Deploy**: connect Vercel (frontend) and provision a VPS for
      Traccar + backend.
