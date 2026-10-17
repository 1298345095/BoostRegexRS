# 固定 ICU 77.1 的纯 Rust 排序键实现路线

日期：2026-10-17。范围是 Boost.Regex 1.89.0 的 ICU traits `transform_primary` / `transform`；这是源码可行性调查和下一阶段原型方案，**尚未实现或验证 Rust 完整排序键**。

## 推荐结论

推荐建立自有、版本固定的 `ICU77SortKey` 内部模块，采用 **ICU 77.1 完整 CE 数据及原始迭代语义的纯 Rust 移植**，并实现同版本完整键编码。新补充的非 FCD 对照已经否证“只 fork ICU4X CE，再加 writer 就足够”的路线；不再把该精简数据路径作为完整兼容原型的前置方案。

保留既定兼容目标：不得通过一律预先 NFD、把 surrogate 改成 U+FFFD 或放宽到“排序顺序相同”来消除差异。ICU4X 的 property、case、数据容器及经验证一致的 NFD 功能仍可按模块重用；不必 fork 整个 ICU4X workspace。当前授权已经确定完整行为兼容及发布库不链接 C/C++，此路线无需用户新增语义取舍。

## 已有实测与本轮证据边界

[已完成探针](icu-probe-results.md) 证明简单 case / category / 适配后的基础分类可行；5,290 个有效 PRIMARY / IDENTICAL 排序符号一致。排序符号一致不约束键字节的压缩格式，也不覆盖所有输入。

主线程补充运行 13 个合法 UTF-8 非 FCD 字符串 × 10 locale × 两种强度的 1,560 对比较，得到 **1,415 一致、145 差异、0 未覆盖、0 参考失败**；PRIMARY 全部一致，root 的 IDENTICAL 78 对中有 18 处差异。语料和独立复现入口见 [non-fcd-cases.tsv](../../tools/icu-probe/non-fcd-cases.tsv)、[run-non-fcd.ps1](../../tools/icu-probe/run-non-fcd.ps1)；原始输出在 `target/research/icu-probe/non-fcd/ordering-summary.json`。这证明当前 ICU4X 候选在已允许的普通输入上就不能全面替代 Boost；不是仅缺一个键输出 API。

本子任务只阅读固定源码和新增方案文档，没有修改生产依赖，没有生成 Rust sort key或执行研究 fork。ICU4X 固定源码身份取自已下载 `icu_collator-2.0.0/.cargo_vcs_info.json`：commit `5e404744dd6c9dd7f86aac82586e3fa98ea75f7f`。C++ 对照一律引用 `release-77-1`，避免使用当前 main 的实现。[ICU4X 固定源码](https://github.com/unicode-org/icu4x/tree/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator)

用户已接受的两项边界沿用：公开 `getloc` 保留 Boost 的默认 locale 查询行为；空串生成确定的有效键，访问异常列为明确兼容例外。这里不重新解释或扩大例外。

## 输出契约先固定

Boost 创建两个 ICU collator，分别设置 PRIMARY 和 IDENTICAL。`do_transform` 把 u32 输入转为 UTF-16，调用 `getSortKey`；每个返回字节直接扩展成一个 u32 键元素，**不是四字节打包**。末尾零只在总长度大于 1 时去掉，因此纯终止零 `[0]` 必须保留。其 100 字节栈缓冲和扩容分支也需要等价结果。[Boost 1.89.0 本地固定源码](D:/NewProgram/librime-rs/target/regex-oracle-cache/boost_1_89_0/boost/regex/v5/icu.hpp:52)

内部可以先返回 `Vec<u8>`，traits 适配层再按上述规则转成键序列。验收同时保存 ICU 原始 bytes 与 Boost 暴露的 u32 序列，分别定位编码错误和适配错误。空 PRIMARY 当前约定 `[0]`；空 IDENTICAL 的有效 ICU 字节 `[1,1,1,1,0]` 转成 `[1,1,1,1]`，对应已批准的例外。[空串实测证据](icu-probe-results.md#参考空串边界)

## 源码路径与职责

| 阶段 | ICU 77.1 对应源码 / 符号 | ICU4X 2.0 对应位置 | 实现含义 |
|---|---|---|---|
| 输入到 CE | `UTF16CollationIterator` / `FCDUTF16CollationIterator`、`CollationIterator::nextCE` | `elements.rs` 的 `CollationElements`、`CollationElement32`、`Tag` | contraction、prefix、expansion、Hangul、implicit weight、numeric，不能逐字符独立查表替代 |
| 原始各级权重 | ICU 64-bit CE 及 `collation.h` | `CollationElement(u64)`、`primary` / `secondary` / `NonPrimary` | 保留全部权重和 sentinel，不先按强度丢弃后续级 |
| locale / tailoring | `CollationData`、`CollationSettings`、`CollationTailoring` | root/tailoring provider、`LocaleSpecificDataHolder`、metadata/reordering | root 回退、特殊 locale 默认值、重排均属于数据语义 |
| PRIMARY 至 QUATERNARY 编码 | `CollationKeys::writeSortKeyUpToQuaternary` | `comparison.rs::compare_impl` 只有比较算法 | 需新写键 writer，不能把比较器返回值转成持久键 |
| IDENTICAL 级 | `RuleBasedCollator::writeIdenticalLevel`、`bocsu.cpp` | 比较器以 NFD 分解迭代器比较相同强度尾部 | 需 NFD 及 BOCSU 编码；UTF-8 bytes 或 u32 原值拼接都不等价 |

ICU4X `elements` 是私有模块；`CollationElements`、`CollationElement`、`NonPrimary` 为 `pub(crate)`。`Collator` / `CollatorBorrowed` 的 root、tailoring、reordering、options、NFD 数据也都是私有字段。公开 `compare` 不暴露完整 CE 序列。[固定 elements.rs](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/elements.rs#L844)；[固定 comparison.rs](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/comparison.rs#L381)

ICU4X `provider` 则是公开模块，`CollationData` 的 trie、ces、ce32s、contexts 字段可见；Jamo、diacritics、metadata、reordering、special primaries 也有数据结构。因此可以加载固定数据，但“数据公开”不等于“现成 CE API 公开”。这些 provider Rust 结构明示不稳定；重用时必须固定版本和本地封装，不把它们透传给本库公开 API。[固定 provider.rs](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/provider.rs#L176)

## 三个必须先解决的缺口

### 1. 键压缩需要额外数据与状态

ICU 键编码涉及 primary lead-byte 压缩、各后续级 common-weight run 压缩、case、backward secondary、shifted variable、reordering 和级分隔。不能仅将 CE 的非零各级权重按大端拼接。PRIMARY 本身也存在压缩，不能因只做 PRIMARY 而绕开。[ICU 77.1 keys writer](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationkeys.cpp)

writer 显式接收 `compressibleBytes`；ICU `CollationData` 说明这是 256 项 primary lead-byte 标记。[ICU 77.1 CollationData](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationdata.h#L181) ICU4X 2.0 的公开数据结构没有这张表，`CollationSpecialPrimaries` 只提供 `last_primaries` 和 `numeric_primary`。CE offset 编码中局部出现的 compressible bit，不能据此假定能完整恢复全表。[ICU4X provider 结构](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/provider.rs#L535)

方案：从固定 ICU 77.1 源数据或固定版本构建时导出器取得该表，保存版本、来源、哈希和生成流程。禁止靠黑盒键样本反向拟合这张表。数据生成工具可依赖参考 C++；发布 Rust 库只携带生成的静态数据，不在用户安装时调用 ICU。

### 2. 始终 NFD 可能改变上游可观察行为

ICU4X 官方实现说明明确：精简数据省略 canonical closure，始终在运行时 NFD，normalization 无法关闭；其 contraction 和 normalization 逻辑并不是 ICU4C 的逐行迁移。[ICU4X 固定实现说明](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/docs.rs#L71)

ICU 77.1 写键按 `settings->dontCheckFCD()` 选择普通 UTF-16 或 FCD 迭代器；IDENTICAL 级另外执行 NFD。故“IDENTICAL 最后都 NFD”不能证明前面的 secondary / tertiary 字节相同。[ICU 77.1 RuleBasedCollator](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/rulebasedcollator.cpp#L1253)

默认设置的来源也必须保留：`CHECK_FCD` 是 options 的 bit 0；`CollationSettings` 构造器只初始化默认 strength 和 maxVariable，未置该位，但 locale 二进制加载会以 `IX_OPTIONS` 中的 options 覆盖，所以不能从构造器推导全部 locale 都关闭 normalization。应从参考 `getAttribute(UCOL_NORMALIZATION_MODE)` 导出每个实际 collator 的生效设置。Boost 只改变 strength，保留其余 locale 默认值。[settings 构造与 bit](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationsettings.h#L30)；[加载时覆盖 options](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationdatareader.cpp#L392)；[Boost 设置 strength](D:/NewProgram/librime-rs/target/regex-oracle-cache/boost_1_89_0/boost/regex/v5/icu.hpp:52)

后续实际查询已完成：[collator-settings.tsv](assets/icu-probe/empty-keys/collator-settings.tsv) 中 th_TH 为 ON，其余九个被测 locale 为 OFF，PRIMARY 与 IDENTICAL 设置一致；请求、有效、实际数据 locale 同时记录。非 FCD 对照中 th_TH 无差异，其余九组有差异。这个实测不能推导未枚举 locale 的默认设置，完整数据导出仍必须逐项保存。

以下独立语料只用于否证，不改已完成的 24 项基线；每行两侧规范等价，左侧包含下降 combining class：

| 用例 | 左 UTF-8 hex | 右 UTF-8 hex | 关键条件 |
|---|---|---|---|
| a + acute + cedilla | `61cc81cca7` | `61cca7cc81` | CCC 230 → 202 |
| á + cedilla | `c3a1cca7` | `61cca7cc81` | 预组字符分解后形成下降 CCC |
| a + U+0315 + grave | `61cc95cc80` | `61cc80cc95` | CCC 232 → 230 |
| α + U+0345 + grave | `ceb1cd85cc80` | `ceb1cc80cd85` | CCC 240 → 230 |

这四组建议已用于构造新增独立语料，且上述门槛已实测失败。PRIMARY 相等不足以通过；实际有 145 个 IDENTICAL 排序符号不同。下一步可用显式 normalization ON 的 ICU 作为归因控制组，但不把控制组语义替换成默认契约。完整 canonical-closure 数据及相应迭代语义成为推荐路线；精简 ICU4X CE 不能只靠 writer 修复该差异。

### 3. surrogate 和实际输入域

ICU4X CE 迭代器以 `char` 为输入，官方说明其 UTF-16 入口把未配对 surrogate 视为 U+FFFD。[ICU4X 输入说明](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/components/collator/src/docs.rs#L94) Boost 的实际 u32→u16 转换、非法码点和未配对单元必须另做入口检查，不能拿本轮逐码点分类的 surrogate identity 策略推导排序行为。

研究 fork 的 `char` 限制不能仅改函数签名成 `u32` 解决：NFD trie、context、隐式权重及 UTF-16 解码都要保留来源语义。若输入已被上游契约拒绝，记录拒绝位置和错误；若可进入 collator，须与固定 ICU 实测。UTF-8 TSV 无法承载这些输入，应增加独立 u16 / u32 二进制协议。

## 数据重用与 fork 的具体边界

ICU4X source provider 会把 ICU export TOML 转为 root / tailoring trie、CE32、CE、context 等表；2.0 固定 commit 声明的测试数据 tag 是 `icu4x/2025-05-01/77.x`，CLDR 是 `47.0.0`。这说明版本族相符，不能替代与 ICU **77.1** 的逐项数据身份核对。其 locale 文件名转换还处理 traditional、phonebook、dictionary 和汉字排序别名，不能只把 `_` 改成 `-`。[source provider](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/provider/source/src/lib.rs#L100)；[collator 数据转换](https://github.com/unicode-org/icu4x/blob/5e404744dd6c9dd7f86aac82586e3fa98ea75f7f/provider/source/src/collator/mod.rs)

原先考虑的**最小研究 fork**只需 `icu_collator` 2.0.0 的 `elements.rs`、provider helper、options bitfield、locale loading，加同 crate writer；不必 fork 整个 ICU4X。然而这仅解决可访问性，不能解决已实测 normalization 差异，故不推荐继续把它当完整兼容主线。该边界分析可用于复用数据容器或诊断 CE 的小工具，不能据此选定生产 CE 后端。

只复制 `elements.rs` 到外部模块并不足够：它调用 provider 的 crate-private helper，使用 options / constants 和 NFD 数据。仅把这些 helper 全改 public 会把不稳定实现扩大为本库长期 API；同 crate 内部 writer 能减少这类新增边界。生产落地时内部独立包可重命名，外部仅暴露 traits 所需能力。

**采用的候选模块边界**：`data77` 保存完整 trie / CE32 / CE / contexts / Jamo / normalization 数据、locale settings / alias / reordering / compression 表；`ce77` 移植普通 UTF-16 与 FCD 迭代行为；`key77` 移植各级权重编码；`identical77` 处理 NFD + BOCSU；`boost_traits_adapter` 处理输入转换、locale 查询契约、字节到 u32 及末尾零。完整数据从固定源码导出，不从参考键反推映射。各模块可独立产出 trace，定位错误来源。[ICU77 数据与迭代器接口](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationiterator.h)

第一版生成链建议从同版完整源码编译一个**开发期专用**导出器，直接导出上述实际表和设置，保留版本/哈希/locale清单。标准 ICU77 `icuexportdata` 不能未经检查就假定具备 ICU4X 分支的 collation TOML 输出；ICU4X source provider 所读的是指定 export snapshot。生产包只携带 Rust 数据。若后续改成直接解析 `.res` / `ucadata.icu`，必须先对照现有导出器验证数据等价；这不是最小原型前置项。

源算法取自 ICU77；复用的 ICU4X 组件固定 2.0.0；所有导入保留许可、来源和修改清单。ICU4X NFD 组件只在验证一致的 IDENTICAL 尾级复用，不强制应用到其它级。无需依赖 C++ 正则实现或把整个 ICU API 重写后才能开始。

## 最小可行原型与停机条件

1. **固定完整数据和诊断契约。** 归档现有非 FCD 失败语料、导出 active locale / collation type / normalization / alternate / case / backward-secondary / numeric / reordering，以及完整表来源。另行检查 surrogate 入口。保持默认设置，不改变输入语义。
2. **root PRIMARY 原型。** 开发期从 ICU77 完整数据导出为 Rust 表；移植 CE32 / CE lookup、普通 UTF-16 迭代、root 必需的 expansion / contraction / Hangul / implicit 权重，再做 primary compression、结束标记和 Boost 键适配。先涵盖 ASCII、重音、Han、Hangul、supplementary、忽略字符和长 common run；输入未支持时显式标记。完整 bytes 必须相同。此阶段没有 IDENTICAL、tailoring 完成的含义。
3. **root IDENTICAL 原型。** 实现 secondary、case（按设置）、tertiary、quaternary 的 writer 状态，再加 NFD + BOCSU identical 级；必须修复本轮 root 18 个差异，而不是只通过原24项。BOCSU 是对码点差值的有状态编码，存在块中点与 Unihan 特例；不可替换成通用 UTF 编码。[固定 BOCSU](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/bocsu.cpp)
4. **加入 tailoring 与 FCD 路径。** 接入已测十 locale 的完整表和实际 normalization 设置，同时覆盖传统西班牙 contraction、ß expansion、土耳其 case、加拿大法语 backward secondary、泰文 shifted、汉字重排、日文 kana；非 FCD 集合全部145个排序差异应消失，并通过完整键。再枚举完整 ICU77 locale / collation type 集合；十 locale 不是最终范围。
5. **输出复现证据。** 固定源码/数据哈希、每层 CE/权重/bytes、差异最小反例、构建工具链与文件身份。仅在键值逐元素通过时声明该原型覆盖完成；资源、六目标和性能仍按独立验收执行。

## 原型验收集合

| 集合 | 必须验证 |
|---|---|
| 现有 24 × 10 × 2 基线 | 470 个有效 Boost 键逐元素对照；已批准空 IDENTICAL 单列有效键预期与例外身份，不把异常输出替换成成功 oracle |
| normalization | 上述非 FCD、leading nonstarter、组合符重排、预组/分解、長 combining sequence；分别记录默认及控制组 settings |
| 压缩边界 | 同 primary lead 的长串、跨 lead / 重排边界、common-run 阈值前一项/阈值/后一项、多段 flush、各级 ignorable；阈值从 ICU77 常量取得 |
| tailoring | prefix / contraction / discontiguous contraction / expansion、backward-secondary 分段、shifted / max-variable、locale 默认 case、数字连续段 |
| 编码和终止 | 空串、内嵌 NUL、U+FFFE / U+FFFF、未指派码点、补充平面、独立 surrogate / 非法入口、键长 99/100/101 及更长 |
| 一致性性质 | 同 settings 下键字典序与 ICU 排序比较一致；规范等价仅在来源实际设置保证时断言；键本身逐 bytes 才是主要验收 |
| 输入穷举与组合 | 全 scalar 单字符键、上下文相关字符的生成序列、固定种子的随机串；单字符穷举不代替 contraction / prefix 覆盖 |

真实维护成本是自有键 writer 和固定数据生成链；完整兼容目标下不能通过改用普通 ICU4X compare 来省掉。是否永久保留 fork、如何包装内部 crate，属于原型证据齐备后的实施选择，当前不需要用户放宽已有契约。
