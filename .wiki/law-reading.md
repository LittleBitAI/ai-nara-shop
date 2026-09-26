---
scope: project
severity: contract
triggers: ["법령", "조문", "항목표", "시행령", "시행규칙", "집행기준", "예규", "판로지원법", "라벨러\\s*프롬프트", "도메인\\s*지식"]
reads: [docs/items.md, docs/rules.md, docs/qna.md]
sources: [reports/labels-600/citation-audit.md, reports/team-c/law-index/README.md, reports/team-c/a1-company-size/result.md, reports/team-c/a2-competitive-product/README.md]
---

# How to read the provided legal package — Do not trust the item table citations as they are

Rule. Legal knowledge combined with judgments, labels, and prompts comes only from the distribution snapshot (`open/data/법령패키지/`). Explanations or revision histories obtained through web searches are not to be moved to any pipeline, wiki, or prompt — they are subject to reproducibility evaluation (R15).
Citations of articles in `항목표.json` are only a starting point. Since citations for each item may be excessive, insufficient, deleted clauses, or orphans, confirm the judgment of [citation audit](../reports/labels-600/citation-audit.md)] and narrow it down to the paragraph or item level before using the fragment.

Why. The first labeler excerpt version cut out the core of v23 (Criteria for Determining Successful Bidders, Chapter 7, Section 3, 2.c), v20 lacked the mandatory clause (Guidelines Article 3②) in the citation, and v22 had only `삭제` as the cited clause. If you move the item table as is, all of this will be missing.

## System — What fills what

| Layer | Provided file example | Role |
| --- | --- | --- |
| Law | National contract Act, 지방계약법, Public Procurement Support Act, Software Promotion Act, Framework Act on Small and Medium Enterprises | Principles and delegation |
| Enforcement Decree | National Enforcement Decree Article 21, Local Enforcement Decree Article 20, Public Procurement Support Act Enforcement Decree Article 2-2 | Cases where restrictions are possible and their targets |
| Enforcement Rule | National/Local Enforcement Rule Article 17, Article 24, Article 25 | Criteria for restrictions (amount, multiple, regional scope, prohibition of duplication) |
| Detailed Regulations/Execution Standards/Decision Criteria | Government Bidding/contract Execution Standards, Local Bidding and contract Execution Standards, Joint contract Operation Guidelines, Criteria for Determining Successful Bidders | Practical standards and lists of prohibited cases |
| Public Notice/Guidelines | Public notice amount, competitive product designation details/detailed product name CSV, Small and Medium SW Business Guidelines | Amount, item, lower limit table |

The lower layer fills what the upper layer delegates by saying "determined by ○○ decree." A judgment for an item usually stands only when reading the Enforcement Decree (permitted restrictions) and the Enforcement Rule/Execution Standards (those criteria and prohibited cases) together.

## Address — Article, Paragraph, Item, Sub-item and the second system

- Laws, Enforcement Decrees, and Enforcement Rules are `제N조(제목)` → Paragraph `①` → Item `1.` → Sub-item `가.`. There are branch articles like `제2조의2`.
- Execution Standards and Decision Criteria are `제N장` → `제N절` → `1.` → `가.` → `1)` → `가)`. There is not a single `제N조` in the 「Criteria for Determining Successful Bidders」.
- Appended tables are attached after the addenda. The `[별표1]` in the main text is just a reference, and the actual appended table section is after a single `[별표]` line.
- Do not include an entire article. Enforcement Decree Article 21 is 2,646 characters long, but only item 10 is needed for v14~v18. Fragments are cut by paragraph/item level using `reports/labels-600/build_excerpt.py`'s `paragraphs()`·`subparagraphs()`.

## Reading sentences

- `다만, …` is a proviso detached from the previous sentence. Judgments are divided by the proviso, such as the public notice amount condition for performance restrictions (Execution Standards Article 5① proviso).
- `삭제 <날짜>` means there is no clause. If the citation only contains deleted clauses (v22), the judgment is made based on the item name and general prohibition clauses (Enforcement Rule Article 17).
- `준용한다`·`제N조에 따른` bring in other articles. If the brought-in article is not in the citation, it is an orphan fragment.
- `미만` excludes boundaries, while `이상`·`이내` include them. The estimated price is meta `입찰추정가격`, and if absent, it is `배정예산금액`.

## National and Local are different laws

Select with meta `적용계약법`. Even for the same topic, the numbers are different.

| Topic | National | Local |
| --- | --- | --- |
| Regional restriction upper limit (goods/general services) | Enforcement Rule Article 24 → Public notice amount 230 million KRW | Enforcement Rule Article 24 + Notice S6: City/Province 350 million KRW, Sejong/City/County/District 500 million KRW |
| Performance scale criteria | Within 1x (limited to public notice amount or more) | Within 1/3, 1x if necessary |
| Minimum joint implementation share | 10% or more | 5% or more (20% range adjustment) |
| Regional/performance restrictions for small-sum private contracts | No corresponding clause | Chapter 5 Private contract Guidelines allow city/county restrictions, performance, and duplication |
| Timing of explanation for negotiation request for proposals | No corresponding clause (v23 is local only) | Criteria for Determining Successful Bidders Chapter 7 Section 3 2.c |

## Four axes that divide items

1. Amount range — 100 million KRW, public notice amount, regional restriction upper limit. Most items are first divided by range (v2·v5~v8·v14~v18).
2. contract method — Private contract, negotiation, restricted competition. The same phrase is a violation in competitive bidding, but normal in small-sum private contract estimates.
3. Target — Whether it is a competitive product (Public Procurement Support Act Article 7). Catalogs also include services. If it is a competitive product, use the table for v10~v13, otherwise v14~v18.
4. Substance of participation qualification — Not the title, law name, or list of submitted documents, but whether it is a sentence that actually filters those who can participate in the bidding.

## What is not here

Judgment rules by item are in [item-guide.txt](../reports/labels-600/item-guide.txt)], management interpretations are in [qna](../docs/qna.md)],
and the fragment list and sizes are owned by [build_excerpt.py](../reports/labels-600/build_excerpt.py)]. This page only contains how to read.
