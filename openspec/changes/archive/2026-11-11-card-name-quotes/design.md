# Design

## Context

- 2026-11-11 explore:zh-TW 有 73 個範本以《{card}》《{spell}》《{source}》括卡名,ja 5 個、en 1 個;app.js 4 處寫死。卡片效果文(日文與我們的中文)都以「」括卡名、《》括效果名。使用者決定都改成「」,戰術名也是。

## Decisions

### D1:括號的分工

- 卡名、戰術名:zh / ja 用「」,en 用 “ ”(en 既有的寫法)。
- 效果名:《》(`ui.card_with_attr`、《格闘》)。
- 魔書名:《》(書名號,`builder.new_from_deck`)。
- 場上的魔物(某一隻):〔〕,不變。

### D2:app.js

- 新增 `ui.quoted_card`(zh / ja「{card}」、en “{card}”),`《${cname(n)}》` 的 4 處改用它。

### D3:守門測試

- 各語言範本中 `{card}`、`{spell}`、`{source}` 前後不可是《》;app.js 不可有 `《${`。
