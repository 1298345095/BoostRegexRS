# ICU 字符规则与排序探针实测

日期：2026-10-17。Q27 已接受的基准为 Boost.Regex 1.89.0、ICU4C 77.1、Unicode 16.0.0、CLDR 47。本轮完成独立研究探针，不是正则引擎交付或生产依赖选型完成。

## 结论

**ICU4X 2.0 加小范围兼容适配，可以覆盖本轮全量逐码点测试；排序不能仅补一个键输出接口。** 最初 24 个字符串的有效排序比较未发现差异，但后续非 FCD 语料实测发现 145 对差异，详见下文；字符名称反查也仍需专门实现。参考空串访问异常与 `getloc()` 查询行为已分别由 Q29 / Q28 决定，记录于 ADR-0005。

| 检查 | 范围 | 结果 |
|---|---|---|
| 原生简单 lower / upper / fold | 每项 1,112,064 个 Unicode scalar | 零差异；每项另有 2,048 个 surrogate 不被 Rust `char` 接受 |
| 原生 General Category | 1,114,112 个码点，含 surrogate | 零差异 |
| 原生 WhiteSpace 对 ICU `u_isspace` | 1,114,112 个码点 | U+001C–U+001F 四处差异 |
| 兼容适配的九字段 | 每字段 1,114,112 个码点，共 10,027,008 次比较 | 零差异、零未覆盖 |
| PRIMARY / IDENTICAL 比较符号 | 24 个字符串 × 10 locale × 两种强度，共 5,520 对 | 5,290 对一致，零 Rust 差异；230 对因参考键失败无法判定 |
| 完整排序键序列 | 参考侧请求 480 个键 | 470 个有效键、10 个访问异常标记；Rust 无对应输出，**未通过验证** |
| 字符名称反查 | 15 个参考用例 | 已记录 Boost 输出；尚无 Rust 对照 |
| locale 状态 | 10 个 locale | `imbue` 保存请求值，但 `getloc` 均返回本机默认 `en_US` |
| 补充非 FCD 语料 | 13 个字符串 × 10 locale × 两种强度，共 1,560 对 | 1,415 对一致、145 对不一致，全部差异在 IDENTICAL；无参考错误或未覆盖 |

逐码点参考直接调用 Boost traits 使用的 ICU 基础函数；不等于已验证 Boost 的属性别名、类别组合或完整正则语义。数字只覆盖 radix 10、16、36，尚未穷举全部合法 radix。数据域为 U+0000..U+10FFFF；超出 Unicode 码点域的数值不在本轮覆盖内。

## 实测身份与复现

本机 Windows x86-64 MSVC；C++ 参考编译器 `_MSC_VER=1951`；Rust stable 实际为 `rustc 1.98.1 (48a229cea 2026-09-01)`。参考运行时报告 ICU 77.1、Unicode 16.0、CLDR 47.0、数据 77.1；使用用户提供的完整 Boost 源码。官方 ICU Windows x64 发行包的 SHA512 已与发行清单核对，DLL、Boost 头文件及输出摘要见 [reference-manifest.json](assets/icu-probe/reference-manifest.json)。没有修改 `librime-rs` 或其参考源码。

ICU4X 组件及编译数据全部精确固定到 `=2.0.0`，使用独立 [Cargo.lock](../../tools/icu-probe/rust/Cargo.lock) 和 `--locked`；根 crate 未加入这些依赖。详见 [Rust 探针说明](../../tools/icu-probe/rust/README.md)。数据版本声明与锁定依赖的源码对应，不依赖当前 Rust 标准库的 Unicode 版本。

统一入口：

```powershell
pwsh -NoProfile -File tools/icu-probe/run.ps1 -BoostRoot D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0
```

原始大文件、下载包、二进制及构建日志放在忽略目录 `target/research/icu-probe/`。关键结果的固定快照在 [assets/icu-probe](assets/icu-probe/)。本次统一入口应返回 **1**：代表参考覆盖不完整，不是所有项目通过；构建或输入格式错误则单独报错。比较器六项回归检查已通过，覆盖颠倒排序、unsupported、缺失、重复以及参考访问异常不能被误算为通过。Rust release 构建和 `clippy -- -D warnings` 通过。

## 适配规则及证据边界

适配器独立根据 ICU / Unicode 规则计算答案，没有从参考输出生成映射：surrogate 的简单大小写保持原码点；blank 为 TAB 或类别 Zs；space 在 WhiteSpace 上加入 U+001C..U+001F；数字使用固定 Unicode 16 Nd 十位序列及 ASCII / 全角拉丁字母，并按 radix 检查范围。Nd 连续区间长度先验证为十的倍数。这是探针实现，生产实现仍需针对全部合法 radix、输入边界和错误契约验收。

原始字段及适配字段分开记录在 [codepoint-summary.json](assets/icu-probe/codepoint-summary.json)。本轮证明的是固定数据与该九字段的可行性，不能扩展为字符串完整大小写映射、所有 Unicode 属性或整库兼容。

排序采用 root、en_US、tr_TR、de_DE、sv_SE、fr_CA、传统西班牙语、zh_CN、ja_JP、th_TH；语料包括空串、重音规范等价、土耳其 I、ß、kana / Han / Thai、NUL、补充平面字符和长键。参考的完整 u32 键按字典序得到预期符号；候选用 ICU4X Collator 比较。每个输入对都有记录；locale 构造失败会显式标记 unsupported，内部 locale 回退仍属于候选库行为，不能凭有限语料推导 locale 身份一致。

详见 [ordering-summary.json](assets/icu-probe/ordering-summary.json)。ICU4X 2.0 没有公开排序键输出 API；顺序相同不足以验证 Boost `transform` / `transform_primary` 暴露的键值。10 个代表 locale 也不构成产品支持范围限制。

## 参考空串边界

在本机原版 Boost + ICU 77.1 组合下，空串 PRIMARY 返回 `[0]`，IDENTICAL 触发 `0xC0000005`。Boost 收到的是有效地址的空区间；其内部构造的空 UTF-16 缓冲区把 null 和长度零传给 ICU。

独立进程最小复现确认：直接向 ICU 的 IDENTICAL 排序传 null / 0 同样访问异常；传有效哨兵地址 / 0 则成功，原始字节为 `[01,01,01,01,00]`。这是当前 Boost 适配和 ICU null 边界的组合现象，尚不据此归责某一方或推广到其它 ICU / 平台。Boost 键约定去掉末尾终止零后，对应候选结果为 `[1,1,1,1]`。诊断见 [empty-diagnostics.json](assets/icu-probe/empty-diagnostics.json) 及 [最小复现源码](../../tools/icu-probe/reference/empty-probe.cpp)。

探针将实际失败保存为 `ERROR:ACCESS_VIOLATION`，没有以直接 ICU 的成功键冒充 Boost 输出。10 个 locale 各有 23 对 IDENTICAL 比较受影响，共 230 对，全部列入 reference_error。

**Q29 已确认：** Rust 对空串生成确定的有效排序键，把该异常列为明确兼容例外；不复现访问异常，也不改成受控错误。正式契约见 [ADR-0005](../adr/0005-icu-locale-query-and-empty-sort-key.md)。原始 230 对 reference_error 仍保留；后续例外基准与 Rust 验收单独记录，不将原版失败改写为通过。

确认后的补充实测使用有效哨兵地址、长度零，覆盖同一组 10 个 locale，20 次调用全部成功；PRIMARY 包装后均为 `[0]`，IDENTICAL 均为 `[1,1,1,1]`。这只是已批准例外的期望值，Rust 完整键仍未实现。证据见 [empty-keys/keys.tsv](assets/icu-probe/empty-keys/keys.tsv) 及同目录元数据 / 摘要；复现入口为 `pwsh -NoProfile -File tools/icu-probe/reference/run-empty-keys.ps1`，复用首轮下载缓存。

## 补充非 FCD 实测：排序候选的否证

源码调查指出 ICU4X 2.0 的排序会进行 NFD 规范化，而 ICU 的排序路径还取决于参考 collator 的设置。为避免只在常见字符串上误判可替代性，增加 13 个合法 UTF-8 字符串，包含不同组合类次序、预组字符与后续组合符号、起始组合符号和希腊字母。原 24 个用例及结果未修改。

实测得到 1,560 对比较，其中 1,415 对一致、145 对不一致；所有 PRIMARY 比较一致，差异全部位于 IDENTICAL。例如 root 下 `a + U+0315 + U+0300` 对 `a + U+0300 + U+0315`：Boost 原始键字典序为 **大于**，ICU4X 返回 **相等**。这里没有空串参考异常或 unsupported，不能按 Q29 例外豁免。

随后用同版本 ICU 查询实际 collator 设置：[collator-settings.tsv](assets/icu-probe/empty-keys/collator-settings.tsv) 显示 th_TH 的 normalization 为 ON，其余九个 locale 均为 OFF，两种强度一致。本轮 IDENTICAL 差异数为 root / en_US / tr_TR / de_DE / sv_SE / 传统西班牙语 / ja_JP 各 18、fr_CA 为 15、zh_CN 为 4、th_TH 为 0。文件同时记录请求、有效和实际数据 locale，避免把 locale 构造成功直接当作数据身份相同。设置与差异分布支持规范化路径的解释，但没有以开启规范化的控制组取代原版默认契约。

因此，**不能直接使用 ICU4X 2.0 的默认排序行为作为完整兼容实现，也不能假设暴露私有排序元素再附加键编码器就足够**。规范化与数据表示差异需解决；候选的字符映射 / 分类成功结论不受影响。具体源码路线见 [完整排序键实现方案](sort-key-implementation-plan.md)。

复现：先运行首轮 `tools/icu-probe/run.ps1` 构建固定参考与候选，再执行 `pwsh -NoProfile -File tools/icu-probe/run-non-fcd.ps1`。后者复用已构建二进制并记录其 SHA256，退出 1 表示实测差异。语料为 [non-fcd-cases.tsv](../../tools/icu-probe/non-fcd-cases.tsv)，固定结果在 [non-fcd/ordering-summary.json](assets/icu-probe/non-fcd/ordering-summary.json)，完整键、候选符号和运行摘要也在该目录；没有用预先规范化参考输入来消除差异。

## locale 与名称

[locales.tsv](assets/icu-probe/locales.tsv) 记录：请求 `tr_TR` 后，`getloc()` 返回 `en_US`，下一次 `imbue(root)` 却返回 `tr_TR`。内部排序 locale 与公开查询值不同。**Q28 已确认保留 Boost 的可观察查询行为**，避免无意改变接口；默认 locale 不固定为本次机器的 `en_US`，详见 [ADR-0005](../adr/0005-icu-locale-query-and-empty-sort-key.md)。

[names.tsv](assets/icu-probe/names.tsv) 记录 Unicode 正式名称、CJK/Hangul 算法名称、部分 extended 名称、POSIX 名称及单字符回退。例如 `<control-0000>` 和 `<noncharacter-FFFF>` 成功；本轮 `<surrogate-D800>`、`<reserved-0378>`、`LINE FEED (LF)` 返回空。不能把所有 ICU 名称模式都视为成功，也不能假设 Unicode NameAliases 等同 Boost 查找行为。

## 下一阶段具体方案

1. **排序键可行性原型优先。** 补充实测已否证直接复用 ICU4X 默认排序路径。以 ICU 77.1 的数据、元素迭代、各级权重和键编码语义为依据，研究纯 Rust 实现；先验证 root PRIMARY / IDENTICAL 完整键及非 FCD 反例，再加入 tailoring、contraction / expansion 和完整 locale 数据。ICU4X 数据只能在逐项证明兼容后复用，不能通过预先规范化输入或放宽等价性绕过差异。最终库仍不链接 C/C++ ICU，并保留许可来源。
2. **名称原型。** 以固定 Unicode 16 名称数据、CJK/Hangul 算法名称及 ICU extended 名称规则实现反查，按 Boost 顺序处理 POSIX 名称和单字符回退；扩展上述失败用例与大小写、空格、长度、无效名边界。名称数据生成工具和发布时 Rust 数据分开。
3. **补全 traits 能力矩阵。** 穷举 Boost 固定属性别名和组合类别、合法 radix，枚举完整 ICU locale / collation 类型与回退，覆盖 UTF-16 非法序列和 Unicode 域外值的实际入口契约。六目标运行同一套参考与候选对照。
4. **再确定生产模块边界和依赖。** 字符映射 / 分类可以沿用本轮已验证候选；完整键、名称与平台 traits 的实现成本查明后，再冻结引擎接口和生产依赖。保持首版完整迁移要求，`librime-rs` 接入继续暂缓。

这四步是基于本轮证据的后续方案，不表示排序键、名称、六平台、性能或内存门槛已经通过。
