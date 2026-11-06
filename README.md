# wiki-skill

一個 Claude Code 技能：把散落各處的筆記與經驗，編譯成一份可查詢、會持續生長的個人 wiki。

原始檔才是真相來源，wiki 是編譯出來的產物。

## 指令

| 指令 | 做什麼 |
|------|--------|
| `/wiki add` | 把原始檔編譯進 wiki，預設一次一個來源 |
| `/wiki query` | 問問題、產出檔案，再把新洞察寫回 wiki |
| `/wiki search` | 搜尋 wiki 文章 |
| `/wiki lint` | 健康檢查，並找出知識缺口 |
| `/wiki status` | 顯示統計資訊 |

## 安裝

這份技能是照作者自己的環境寫的，直接裝不能用，要先改路徑。

1. 複製到技能資料夾：

   ```bash
   git clone https://github.com/fredchu/wiki-skill ~/.claude/skills/wiki
   ```

2. 改 `SKILL.md` 開頭的 `WIKI_DIR` 和 `SCRIPTS_DIR`。
3. 改 `scripts/inject_context.py` 的 `DEFAULT_WIKI_DIR`。
4. 把 `SKILL.md` 裡的 `vault-git` 換成你自己的 `git`。它是作者自己的包裝指令，這份倉庫沒有附。

## 需要的工具

- Python 3
- [qmd](https://github.com/tobi/qmd)：可選，用來搜尋。沒裝就退回一般文字搜尋。
- Obsidian CLI：可選，`/wiki lint` 用來交叉驗證連結。

## 授權

MIT
