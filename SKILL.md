---
name: wiki
description: >
  Personal knowledge wiki — 把散落在多個位置的知識編譯成統一的、可查詢的、會自我生長的 wiki。
  當用戶說「wiki add」「wiki query」「wiki search」「wiki lint」「wiki status」時使用。
  也適用於用戶問跨專案的綜合性問題時主動建議使用。
argument-hint: add [--source <path>] [--batch] | query <question> [--format markdown|chart|html|slides] | search <keyword> | lint [--fix] | status
---

# Personal Knowledge Wiki

將散落在記憶庫、company lessons、本體畫像的知識編譯成統一的 wiki。
Wiki 是編譯產物，原始檔案是 source of truth。

## 路徑

```
WIKI_DIR=/Users/fredchu/Documents/For_Claude/wiki
SCRIPTS_DIR=/Users/fredchu/dev/wiki/scripts
```

## 子命令路由

根據第一個參數決定行為：

| 參數 | 行為 |
|------|------|
| `add` | 從原始檔編譯進 wiki（預設互動模式） |
| `query` | 問問題 + 產出檔案 + 回流 |
| `search` | qmd hybrid search + Grep fallback |
| `lint` | 健康檢查 + knowledge gap 分析 |
| `status` | 統計資訊 |

---

## `/wiki status`

直接執行腳本：

```bash
python3 ${SCRIPTS_DIR}/wiki_status.py --wiki-dir ${WIKI_DIR}
```

回報結果給用戶。

---

## `/wiki search <keyword>`

### Primary: qmd hybrid search

```bash
qmd search "<keyword>" --json -n 10
```

qmd 結合 BM25 + vector semantic search，比純 Grep 或純語意搜尋更準。

### Fallback: Grep

如果 qmd 沒結果或未安裝，退回 Grep 搜尋 `${WIKI_DIR}/`（排除 `_outputs/`、`_index.md`、JSON 檔案）。

### 輸出格式

回傳：匹配文章標題 + 匹配段落摘要 + backlink count（從 `_backlinks.json` 查）。不修改任何檔案。

### 索引更新

每次 `/wiki add` 完成後自動執行 `qmd update` + `qmd embed`，保持索引同步。

---

## `/wiki add [--source <path>] [--batch] [--dry-run]`

### 預設：互動模式（一次一個 source）

Karpathy 原則：「I prefer to ingest sources one at a time and stay involved」。
增量 add 預設一次處理一個 source，LLM 先與用戶討論 key takeaways 再寫入。

### --batch：批次模式

大量存量檔案（如 initial add）使用。用 Sonnet subagent 並行處理，不逐檔討論。

### Step 1: 掃描待處理檔案

```bash
python3 ${SCRIPTS_DIR}/absorb_log.py --wiki-dir ${WIKI_DIR} [--source <path>]
```

如果是 `--dry-run`，列出待處理檔案後結束。

### Step 2: 逐檔 absorb

#### 互動模式（預設）

對每個待處理的原始檔案：

1. **讀原始檔內容**
2. **向用戶摘要 key takeaways**（2-3 bullet points），問：
   - 「這裡面最重要的是什麼？」
   - 「要強調或跳過什麼？」
   - 如果用戶說「ok」或不回應，按 LLM 自己的判斷繼續
3. **讀 `_index.md`**（了解現有文章全貌）
4. **判斷歸屬**：
   - 這個檔案的內容跟哪些現有文章相關？
   - 需要新建文章嗎？（用具體名詞測試：「X 是一個 ___」）
   - 需要更新哪些現有文章？
5. **讀要更新的每一篇文章**（re-read before edit，不可省略）
6. **整合寫入**：把新知識編織進文章，遵循下方「寫作標準」
   - **Timeline Iron Law**：如果文章 `timeline_enabled: true` 且這次改動觸及結論層（不只補細節），必須同步 append 一條 timeline entry（格式：`- YYYY-MM-DD | 事實 | 來源`）
   - **Original 判斷**：如果原始檔含有用戶自己形成的觀察/判斷/框架（authorship test），考慮建 `original` type 文章而非塞進既有文章
7. **標記完成**：
   ```bash
   python3 ${SCRIPTS_DIR}/absorb_log.py --wiki-dir ${WIKI_DIR} --mark <file_path> --articles <art1>,<art2>
   ```
8. **Log**：
   ```bash
   python3 ${SCRIPTS_DIR}/wiki_log.py --wiki-dir ${WIKI_DIR} --op ingest --detail "absorbed <filename> → <articles>"
   ```

#### 批次模式（--batch）

跳過 Step 2 的用戶討論。其餘步驟相同。可用 Sonnet subagent 並行處理。

### Step 3: Checkpoint（每 15 個檔案）

```bash
python3 ${SCRIPTS_DIR}/rebuild_index.py --wiki-dir ${WIKI_DIR}
```

同時做品質審計：
- 最近 15 個檔案產生了幾篇新文章？如果 0 篇，可能在 cramming
- 挑 3 篇最常更新的文章重讀，確認是主題式結構而非流水帳

### Step 4: 最終 rebuild + qmd sync

```bash
python3 ${SCRIPTS_DIR}/rebuild_index.py --wiki-dir ${WIKI_DIR}
qmd update
qmd embed
```

### Step 5: 自動 commit（不可跳過）

absorb 完成後 **必須 commit wiki 改動**，避免 metadata（_absorb_log / _index / _backlinks / _log）跟新文章脫節。

```bash
cd /Users/fredchu/Documents/For_Claude
git add wiki/
git status --short wiki/
```

**LLM 基於本次 absorb 的內容寫 commit message**（不要機械式「absorb N sources, +X articles」），格式參考：

```
docs(wiki): <核心主題> + <次要主題>（如有）

<2-3 行 narrative：吸收的關鍵 sources、新建文章的核心 insight、
任何 cross-link 決策。讓未來 grep 找得到這次 absorb 的脈絡>
```

範例：`docs(wiki): split llm-driven-ui-patterns from agent-workflow-patterns` (commit 59377cd) — narrative-rich，可事後 forensic。

寫完 commit message 後執行：
```bash
git commit -m "$(cat <<'EOF'
... (LLM 寫的 message)
EOF
)"
```

**不問用戶**（除非有不該 commit 的 untracked 異常檔案）— 這是用戶 audit 2026-04-29 backlog 🟡 #7 確認的 reflex。

### Anti-cramming

如果發現同一篇文章的某子主題已經有 3+ 段落，拆成獨立文章。

### Anti-thinning

只在有 3+ 句有意義內容時才建新頁。寧可先寫在相關文章裡，等素材夠了再獨立。

---

## `/wiki query <question> [--format markdown|chart|html|slides]`

### Step 1: 找相關文章

1. 用 qmd 搜尋：`qmd search "<question>" --json -n 10`
2. 補充：讀 `${WIKI_DIR}/_index.md` 看是否有 qmd 沒抓到的相關文章
3. 如果不確定，用 `/wiki search` 輔助

### Step 2: 深入閱讀

1. 讀找到的文章（3-8 篇）
2. 順著 `[[wikilinks]]` 深入 2-3 層
3. 查 `_backlinks.json` 找高連結度的相關文章

### Step 3: 綜合回答

依 `--format` 產出（預設 markdown）：

| format | 產出方式 | 存放位置 |
|--------|---------|---------|
| `markdown` | 直接寫 .md 檔 | `${WIKI_DIR}/_outputs/YYYY-MM-DD-<slug>.md` |
| `chart` | Python matplotlib 生成圖表 | `${WIKI_DIR}/_outputs/YYYY-MM-DD-<slug>.png` |
| `html` | 生成互動式 HTML（可用 playground skill） | `${WIKI_DIR}/_outputs/YYYY-MM-DD-<slug>.html` |
| `slides` | 生成 Marp 格式 .md | `${WIKI_DIR}/_outputs/YYYY-MM-DD-<slug>.marp.md` |

所有產出同時在 terminal 呈現給用戶。

### Step 4: 回流（Karpathy 飛輪）

把綜合過程中產生的新洞察 absorb 回 wiki：
- 更新相關文章（補上跨文章的連結或洞察）
- 如果回答揭示了新的 pattern 或概念 → 建新文章
- 執行 `rebuild_index.py` 更新索引

### Step 5: Log

```bash
python3 ${SCRIPTS_DIR}/wiki_log.py --wiki-dir ${WIKI_DIR} --op query --detail "<question summary>"
```

### 規則

- Query 只讀 wiki 文章，不讀原始檔案
- 不讀 `_outputs/` 裡的舊 query 結果（避免遞迴引用）

---

## `/wiki lint [--fix] [--scope <directory>]`

### Phase 1: 結構掃描（唯讀）

讀所有 wiki 文章 + `_index.md` + `_backlinks.json`，檢查：

| 項目 | 嚴重度 | 說明 |
|------|--------|------|
| 矛盾 | 🔴 | 同一事實在不同文章有不同說法 |
| 斷連 | 🔴 | `[[wikilinks]]` 指向不存在的文章 |
| 陳舊 | 🟡 | 原始檔 mtime 比 wiki 新（跑 `absorb_log.py` 檢查） |
| 膨脹 | 🟡 | 超過 150 行 |
| 瘦弱 | 🟡 | 低於 15 行 |
| 孤兒 | 🟡 | backlink count = 0 |
| 缺失候選 | 🟢 | 多篇文章提到但沒有頁面的具體名詞 |

### Phase 2: Knowledge Gap 分析

讀完所有文章後，LLM 分析：

1. **缺少的主題**：哪些概念在多篇文章被提及但沒有獨立頁面？（不只看 wikilink，也看文章內文中反覆出現的具體名詞）
2. **薄弱區域**：哪些文章的 sources 數量少於 2，可能需要更多原始素材？
3. **建議去研究的問題**：基於現有知識的缺口，建議 3-5 個值得 deep research 的問題
4. **建議尋找的 sources**：哪些類型的文件（論文、文章、repo）能填補知識缺口？

### Phase 3: 輸出報告

存到 `${WIKI_DIR}/_outputs/lint-YYYY-MM-DD.md`，分四段：
1. 結構問題（🔴🟡🟢）
2. Knowledge Gaps（缺少的主題 + 薄弱文章）
3. 建議研究的問題
4. 建議尋找的 sources

### Phase 4（僅 `--fix`）

- 斷連 → 建 stub 或修正 wikilink
- 陳舊 → 觸發 `/wiki add` re-absorb
- 膨脹 → 拆分（LLM 判斷）
- 矛盾 → 只標記，列給用戶決定

### Phase 5: Log

```bash
python3 ${SCRIPTS_DIR}/wiki_log.py --wiki-dir ${WIKI_DIR} --op lint --detail "<summary of findings>"
```

---

## Logging

所有操作都記錄到 `${WIKI_DIR}/_log.md`（append-only 時間線）。

```bash
python3 ${SCRIPTS_DIR}/wiki_log.py --wiki-dir ${WIKI_DIR} --op <ingest|query|lint|search|status> --detail "<description>"
```

格式：`## [YYYY-MM-DD HH:MM] <op> | <detail>`

用途：
- 追蹤 wiki 的演化歷程
- 回溯「什麼時候 add 了什麼」「上次 lint 發現什麼」
- 可用 `grep "^## \[" _log.md | tail -10` 快速查最近操作

---

## Session Handoff 整合

當 session handoff 完成後（Apple Notes 筆記已寫入），自動檢查是否有新的原始檔需要 add：

1. 執行 `absorb_log.py` 檢查 pending files
2. 如果有 pending → 自動執行 `/wiki add`（不需用戶確認）
3. 如果沒有 → 跳過

這確保 wiki 跟隨每次 session 的產出自動成長。

---

## 寫作標準

所有 wiki 文章遵循以下標準：

### 語調

Wikipedia 風格。扁平、事實導向、中性。

**禁止使用：**
- Em dashes (—)
- Peacock words: legendary, visionary, groundbreaking, deeply, truly
- Editorial voice: interestingly, importantly, it should be noted
- Rhetorical questions
- Progressive narrative: would go on to, embarked on, this journey
- Qualifiers: genuine, raw, powerful, profound

**正確做法：**
- 主詞開頭，平鋪直敘
- 一句一個事實，短句
- 簡單過去式或現在式
- 用歸因取代斷言：「他描述為令人振奮」而非「這令人振奮」
- 讓事實暗示重要性
- 日期和具體細節取代形容詞

### 引用

每篇最多 2 句直接引用。文章中性，引用承載情感。

### 結構

按主題組織，不按時間排列。

| type | 結構 |
|------|------|
| project | 起源 / 發展 / 結果 |
| technique | 用途 / 踩過的坑 / 最佳實踐 |
| person | 角色 / 合作方式 / 影響 |
| tool | 用途 / 設定 / 限制 |
| decision | 情境 / 選項 / 推理 / 選擇 |
| pattern | 觸發 / 循環 / 嘗試打破 |
| research | 動機 / 方法 / 發現 / 結論 |
| original | 觸發情境 / 核心主張 / 推理 / 反例與邊界 / 相關連結 |

### 長度目標

| type | 行數 |
|------|------|
| person (1 reference) | 20-30 |
| person (3+ references) | 40-80 |
| technique / pattern | 40-80 |
| project / research | 40-100 |
| tool / decision | 25-50 |
| original | 20-60 |
| 最低（任何） | 15 |

### 每篇都有一個 point

不是「X 出現了 4 次」，而是「X 在 Fred 的工作中代表什麼」。

### Original Type — 捕捉用戶自己形成的判斷

`original` type 專門存用戶自己形成的觀察、框架、hot take、心智模型。跟其他 type 的區別：

- `research` = 整理外部研究
- `technique` = 做某件事的模式
- `decision` = 某次選 A 不選 B 的理由
- **`original` = 用戶對世界的觀察/判斷/框架，用用戶的原話**

**Authorship test（判斷是不是 original）：**
- 這個想法是用戶自己生出來的嗎？→ 是就是 `original`
- 用戶對別人想法的獨特綜合？→ 綜合本身是原創 → `original`
- 別人提出的概念？→ `concept` 或 `research`

**寫法規則：**
- 核心主張用用戶的**原話**，不清理不改寫。語言本身就是洞察
  - ✅ 「先把流程寫下來，再談自動化」
  - ❌ 「流程文件優先的自動化方法論」
- 反例與邊界：這個主張在什麼情境會失效？限制是什麼？
- 強制交叉連結：每篇 `original` 至少要 2 個 `[[wikilinks]]` 連到相關 concept / person / project / 其他 original。沒連結的 original 是 dead original

**Slug 命名：** 用用戶的原話，不意譯
- ✅ `write-the-process-first.md`
- ❌ `process-first-automation-methodology.md`

**觸發時機（何時建新的 original）：**
- Session 對話中用戶說出結構化的觀察或框架
- 用戶的 MEMORY.md / session handoff 反覆提到同一個判斷
- 用戶對新情境套用過去的判斷時（代表這判斷穩定到值得獨立）

### Timeline Pattern — 演化型文章的證據鏈

靈感來自情報評估模式：結論（compiled truth）可以改寫，證據（timeline）永不刪改。

**何時啟用 Timeline：**

適用於會演化的文章：`project`、`research`、`decision`、`original`，以及 `technique` / `tool` 中會反覆更新的主題（如長期維護的工具或專案）。

不適用於穩定型文章：多數 `person`、單次 `research` 總結。

**啟用方式：**

在 frontmatter 加 `timeline_enabled: true`，並在文章末尾（`## Backlinks` 之前）加 `## Timeline` 區塊。

**Compiled Truth vs Timeline 的分工：**

```
文章主體（Compiled Truth）
 = 當前最佳理解
 = 可以隨時改寫
 = 新讀者看這裡

## Timeline
 = 證據鏈與演化歷程
 = Append-only，永不刪改
 = 想知道「為什麼現在這樣想」看這裡
```

**Timeline Iron Law：**

重寫 compiled truth 時，必須同步 append 一條 timeline entry 記錄這次改動。被推翻的舊結論濃縮成一句話放進 timeline，不是消失。違反這條 = 破壞 timeline 的價值。

**格式：**

```markdown
## Timeline

- 2026-04-12 | 新 API 接通，重新整理資料流程 | session handoff 2026-04-11
- 2026-03-29 | 從手動同步改為排程同步 | lessons/sync-decision.md
- 2026-03-15 | 初版設計確立 | company/example/work-log/
```

規則：
- 最新在上（反時序）
- 一行一個事件，多行可縮排
- `- YYYY-MM-DD | 事實摘要 | 來源` 格式（用 pipe 分隔，避免 em dash）
- 只追加，不編輯已有項目
- 絕不刪除任何項目

### 連結

用 `[[wikilinks]]` 連結文章。在 frontmatter `sources:` 記錄原始檔路徑。

### 文章格式

```yaml
---
title: Article Title
type: project | technique | person | tool | decision | pattern | research | original | life
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
timeline_enabled: false  # 演化型文章設 true，預設 false
related: ["[[Other Article]]", "[[Another]]"]
sources:
  - "path/to/original/file.md"
---

# Article Title

{Compiled Truth：當前最佳理解，按主題組織，可改寫}

## Timeline

<!-- 只在 timeline_enabled: true 時存在 -->
<!-- Append-only，永不刪改。格式：- YYYY-MM-DD: 事實 — source: 來源 -->

## Backlinks

{由 rebuild_index.py 自動產生}
```

### 並行規則

- 永遠不刪除或覆蓋檔案之前先讀取
- 編輯文章前立即重讀（re-read before edit）
- 不修改 `_absorb_log.json`（只透過 absorb_log.py --mark）
- 只在命令結束時才 rebuild `_index.md` 和 `_backlinks.json`
