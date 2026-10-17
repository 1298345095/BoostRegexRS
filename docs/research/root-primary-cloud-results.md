# 云端参考环境与纯 Rust root PRIMARY 排序键实测

日期：2026-10-17。范围：官方 Boost.Regex 1.89.0、ICU4C 77.1 / Unicode 16.0.0 / CLDR 47 下，root locale、PRIMARY 强度的完整排序键原型。

## 1. 阶段结论

[cloud-handoff.md](cloud-handoff.md) 定义的首轮云端工作已经实际执行：取得并核验官方依赖，在项目局部目录建立参考环境，重放已提交语料，从完整 ICU77 数据生成固定 Rust 数据，实现并运行纯 Rust root PRIMARY 排序键。最终统一运行完成于 **2026-10-17 10:41:24 UTC**，全程返回 **0**；结果标记为 `stage_status: passed`、`coverage_profile: full_recorded_suite`。[统一结果](assets/icu77-cloud/primary/cloud-summary.json)

本轮 **1,160,181 条合法输入记录**同时通过完整 ICU 原始字节序列与实际 Boost 暴露的 u32 键序列对照；另有 **11 条非法输入按预期拒绝**，没有混入有效键通过数。记录范围内为 **0 差异、0 未支持、0 参考错误**。这里统计的是输入记录，各集合可以包含相同字符串；没有把这些记录称为互不重复的字符串。[PRIMARY 汇总](assets/icu77-cloud/primary/summary.json)

附加检查有两类：48,105 次相邻输入的 ICU 比较符号与键字典序一致；对 directed 和 context 两组的 **28,108 条完整 CE64 序列**逐元素对照也全部一致，包括 PRIMARY 会忽略的权重和结束 sentinel。这些是同一批输入的补充诊断，不能重复计入有效键数，也不等于 IDENTICAL 键已经实现。[directed 键结果](assets/icu77-cloud/primary/directed/summary.json)、[generated 键结果](assets/icu77-cloud/primary/generated/summary.json)、[context 键结果](assets/icu77-cloud/primary/contexts/summary.json)、[directed CE 结果](assets/icu77-cloud/primary/ce-audit-final-directed/summary.json)、[context CE 结果](assets/icu77-cloud/primary/ce-audit-final-contexts/summary.json)

原型保留在独立的 [研究 crate](../../tools/icu-probe/primary/rust/Cargo.toml)，根库公开 API 和完整正则引擎仍未实现。本报告只确认上述环境、固定数据和记录输入的结果；IDENTICAL、多 locale、六平台、引擎性能与内存验收，以及 `librime-rs` 接入均不在完成声明内。原先发现的 **145 对 ICU4X IDENTICAL 差异仍然存在**，本轮没有将其改写为通过。[ADR-0001](../adr/0001-boost-regex-behavioral-compatibility.md)、[ADR-0002](../adr/0002-native-dependencies-and-platform-semantics.md)、[ICU4X 非 FCD 重放结果](assets/icu77-cloud/non-fcd/ordering-summary.json)

## 2. 实际环境、固定来源与许可证

### 实际运行环境

本轮在云端 Linux x86-64 容器运行。用户空间为 **Ubuntu 24.04.3 LTS、glibc 2.39**；实际内核为 **Linux 6.18.55**。C/C++ 编译器为 **GCC 13.3.0**，GNU Make 为 4.3，Python 为 3.12.14。ICU 以完整数据、shared 和 static 配置构建，安装在 `target/research/icu77-cloud/install/icu`；没有使用任意版本的系统 ICU 代替基准。[环境与构建 manifest](assets/icu77-cloud/environment-manifest.json)

实际 Rust 工具链为 **stable 1.99.1**，`rustc 1.99.1 (58cf8f9c3 2026-10-13)`、`cargo 1.99.1 (5f94df478 2026-08-27)`，目标为 `x86_64-unknown-linux-gnu`，LLVM 23.1.1。工具链从官方 2026-10-15 的 stable channel 取得，先验证 channel manifest 的官方 SHA256，再验证 rustc、Cargo、标准库、rustfmt、Clippy 组件的摘要，安装到项目内。[工具链 manifest](assets/icu77-cloud/primary/rust-toolchain-manifest.json)、[工具链准备脚本](../../tools/icu-probe/cloud/rust_toolchain.py)

当前容器的编译器加载适配使用项目局部库目录，并记录 `RUSTFLAGS=-C link-arg=-fuse-ld=bfd`；没有修改已核验的官方编译器二进制。固定这次工具链身份是为了复现测量，不是新增历史最低 Rust 版本承诺。字符数据由 ICU77 静态文件固定，不随 Rust stable 或宿主 Python 的 Unicode 数据库变化。[ADR-0002](../adr/0002-native-dependencies-and-platform-semantics.md)、[工具链 manifest](assets/icu77-cloud/primary/rust-toolchain-manifest.json)、[生成语料身份](assets/icu77-cloud/primary/cases/generation.json)

### 官方依赖及摘要

| 依赖 | 实际取得的官方文件 | 核验方法 |
| --- | --- | --- |
| Boost 1.89.0 | [boost_1_89_0.tar.bz2](https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2) | 与官方同名 `.json` 的 SHA256、脚本固定摘要和下载文件实际摘要三者对照 |
| ICU4C 77.1 | [icu4c-77_1-src.tgz](https://github.com/unicode-org/icu/releases/download/release-77-1/icu4c-77_1-src.tgz) | 与官方 [SHASUM512.txt](https://github.com/unicode-org/icu/releases/download/release-77-1/SHASUM512.txt) 的 SHA512、脚本固定摘要和实际摘要三者对照 |
| ICU 完整数据 | 上述源发行包内 `source/data/in/icudt77l.dat` | 保留完整数据，不应用过滤；生成器再次与已核验 archive 内原字节比较 |

实际固定摘要如下；下载地址、文件大小、清单身份和构建产物 SHA256 同时保存在 [环境 manifest](assets/icu77-cloud/environment-manifest.json)。本轮核验官方摘要，**未验证 detached signatures**，没有将摘要核验描述为签名核验。

```text
Boost 1.89.0 archive SHA256
85a33fa22621b4f314f8e85e1a5e2a9363d22e4f4992925d4bb3bc631b5a0c7a

ICU4C 77.1 source archive SHA512
a47d6d9c327d037a05ea43d1d1a06b2fd757cc02a94f7c1a238f35cfc3dfd4ab78d0612790f3a3cca0292c77412a9c2c15c8f24b718f79a857e007e66f07e7cd

Unfiltered icudt77l.dat SHA256
310d9b2cb42947fad7f388b09d2ae574e2adeb60ca76abf280438908f20b2d7b
```

参考程序实际查询到 ICU 77.1、Unicode 16.0、CLDR 47.0、ICU data 77.1；原型导出器还记录了 root collation version `[153,128,0,0]`。版本不匹配会使生成或参考运行失败，不能仅凭头文件版本号接受一个不同数据来源的运行库。[参考 metadata](assets/icu77-cloud/baseline/reference-metadata.json)、[数据生成 manifest](assets/icu77-cloud/primary/data-generation-manifest.json)

ICU 源发行包的完整许可证已经原样保存为 [LICENSE-ICU.txt](../../tools/icu-probe/primary/data/LICENSE-ICU.txt)，算法与数据源文件、版权归属和 Rust 表示变更见 [NOTICE.md](../../tools/icu-probe/primary/data/NOTICE.md)。Boost 参考源码保持外部开发依赖，遵循随发行包提供的 BSL-1.0；其许可证身份也记录在环境 manifest。Rust 的字节到 u32 包装根据固定 Boost traits 行为独立实现，原型运行时不链接 Boost。

## 3. 云端参考适配与历史证据重放

### 参考工具适配

新增 [prepare.py](../../tools/icu-probe/cloud/prepare.py)、[reference.py](../../tools/icu-probe/cloud/reference.py)、[replay.py](../../tools/icu-probe/cloud/replay.py) 和 [run.py](../../tools/icu-probe/cloud/run.py)。默认下载、源码、构建、安装、工具链和结果均位于 `target/research/icu77-cloud`。现有 PowerShell / MSVC 入口保留；历史 `D:/`、`C:/` 路径只作为历史来源记录，不参与 Linux 编译或运行。

[probe.cpp](../../tools/icu-probe/reference/probe.cpp) 在 Windows 保留原 SEH 路径；Linux 用子进程隔离实际未修改的 Boost 调用，父进程记录真实 signal。新的 PRIMARY 批量参考也通过 [reference_process.py](../../tools/icu-probe/primary/reference_process.py) 保存进程证据，必要时递归隔离 signal 失败的输入，继续保留其余结果。启动失败、普通非零退出、丢失或格式损坏的输出不会被静默改成兼容成功；相关行为由本轮 Python 检查覆盖。[参考构建 manifest](assets/icu77-cloud/reference-build-manifest.json)、[验证日志](assets/icu77-cloud/primary/validation/primary-harness.log)

### Windows 历史键与 Linux 新键

两组已提交语料均从实际输入重放。逐个比较有效键的长度和每个 u32 元素，得到 **730 个有效键全部一致**；空串 IDENTICAL 的 10 个参考错误单列，未混入成功数。[跨平台摘要](assets/icu77-cloud/cross-platform-summary.json)

最终统一 runner 将七项历史重放条件作为阶段门槛，实际全部通过：有效键一致、参考错误状态保留、旧候选符号行一致、码点文件大小 / 摘要一致、九字段适配结果一致、locale 查询契约保留，以及已批准空串例外期望行一致。这里只要求历史差异被忠实重现，没有要求尚未实现的 IDENTICAL 候选变成兼容成功。[统一结果的 historical_replay](assets/icu77-cloud/primary/cloud-summary.json)

| 历史语料 | 请求键数 | 有效键一致 | 有效键差异 | 参考错误键 | 未覆盖 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 24 输入 × 10 locale × 2 强度 | 480 | 470 | 0 | 10 | 0 |
| 13 个非 FCD 输入 × 10 locale × 2 强度 | 260 | 260 | 0 | 0 | 0 |
| 合计 | 740 | 730 | 0 | 10 | 0 |

Windows 历史错误为 `ERROR:ACCESS_VIOLATION`，Linux 实际错误为 `ERROR:SIGNAL_11`。不同平台的错误标记分别保留，没有为了使文件摘要相同而统一错误文本。历史原件继续位于 [assets/icu-probe](assets/icu-probe/)，本轮结果独立位于 [assets/icu77-cloud](assets/icu77-cloud/)；参考键文件的文本摘要可以因换行或错误标记而不同，有效键比较基于解析后的完整序列。

### 旧 ICU4X 候选的成功和差异均保留

旧 ICU4X 2.0 候选仍按其原有职责重放：字符映射 / 分类及适配器检查、排序符号比较。其结果没有被新的 Rust 排序键原型替代或混写。

| 旧候选的排序符号重放 | 比较数 | 一致 | 差异 | 未支持 | 参考错误 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 24 输入基线 | 5,520 | 5,290 | 0 | 0 | 230 |
| 13 输入非 FCD | 1,560 | 1,415 | 145 | 0 | 0 |

上述 **145 对差异全部属于 IDENTICAL**，与历史 Windows 符号记录一致；其中 root 的 18 对仍是下一阶段回归目标。旧候选没有完整键输出，因此该表不能当成键字节验收。新 root PRIMARY 的通过也没有证明这些 IDENTICAL 差异已经修复。[基线重放](assets/icu77-cloud/baseline/ordering-summary.json)、[非 FCD 重放](assets/icu77-cloud/non-fcd/ordering-summary.json)、[历史差异说明](icu-probe-results.md#补充非-fcd-实测排序候选的否证)

重新生成的 `codepoints.bin` 包含 1,114,112 条记录，覆盖全部码点值并包含 surrogate。旧适配器的 lower、upper、fold、category、blank、space、digit10、digit16、digit36 九个字段，共 **10,027,008 次字段比较，0 差异、0 未支持**。原始 ICU4X API 的缺失项与直接差异仍单独记录，例如 `WhiteSpace` 的四个差异不能被描述为未经适配即通过。[九字段结果](assets/icu77-cloud/baseline/codepoint-summary.json)

历史大型 `codepoints.bin` 没有上传，因此这里没有声称重新读取两份历史 / 云端大文件逐字节比较。新生成文件的 **44,564,480 bytes** 和 SHA256 `09d765de08abdebdfd554e4a0d65c843480d231bb87f8cfd9d728e76efd80e14` 与历史 manifest 保留的大小、摘要相等；这项核对和新运行的九字段比较是两项不同证据。[跨平台摘要的 codepoint_reference](assets/icu77-cloud/cross-platform-summary.json)

### `getloc` 和空串例外

历史 Windows 默认 locale 为 `en_US`，本轮 Linux 默认值为 `en_US_POSIX`。各自 10 行 locale 探针均确认：`getloc()` 返回进程默认值，首次 `imbue` 返回默认值，第二次 `imbue` 返回先前实际设置的 locale。因此本轮保留 [ADR-0005](../adr/0005-icu-locale-query-and-empty-sort-key.md) 的原版查询契约，没有把 Linux 默认值改为 `en_US`，也没有把 `getloc` 改为返回最近设置的排序 locale。当前独立 root 原型尚不提供最终库的 locale 查询 API。[locale 查询核对](assets/icu77-cloud/cross-platform-summary.json)

空串 PRIMARY 正常返回 ICU `[00]`、Boost `[00000000]`。原版空串 IDENTICAL 的 10 次崩溃继续是参考错误，会影响旧候选的 230 对比较。按 ADR-0005，用有效哨兵地址 / 长度零进行的独立参考调用，在 10 locale × 2 强度的 20 次调用中全部成功；例外期望仍是 PRIMARY `[0]`、IDENTICAL `[1,1,1,1]`。这些期望值与历史相等，但不会替代原版失败记录，也不表示 Rust IDENTICAL 已经通过。[空串例外 metadata](assets/icu77-cloud/empty-keys/metadata.json)、[例外完整键](assets/icu77-cloud/empty-keys/keys.tsv)、[原版诊断](assets/icu77-cloud/empty-diagnostics.json)

## 4. 固定数据链与纯 Rust 实现

### 完整 root 数据导出

[export-root.cpp](../../tools/icu-probe/primary/export/export-root.cpp) 通过固定 ICU77 的 `CollationRoot`、`CollationData`、`CollationSettings` 和 `UCharsTrie` 导出完整 root 数据。它不读取测试输入，也不调用排序键接口来建立答案表。原始 CE32、CE64、Jamo、contexts 和 256 项压缩标记均保留；完整 trie 的码点映射改为等值 ranges，并另外枚举 context trie 的完整 UTF-16 key，供 Rust 建立自己的查询结构。[生成说明](../../tools/icu-probe/primary/export/README.md)、[二进制格式](../../tools/icu-probe/primary/data/FORMAT.md)

| 导出部分 | 实际数量 |
| --- | ---: |
| 全码点 CE32 ranges | 85,290 |
| 原始 CE32 table | 6,145 |
| 原始 CE64 table | 2,023 |
| 原始 context UTF-16 units | 4,603 |
| Jamo CE32s | 67 |
| Primary compressible flags | 256 |
| 全码点 FCD16 ranges | 1,036 |
| Decoded context tries | 77 |
| Decoded context entries | 1,147 |

固定的 [root-icu77.bin](../../tools/icu-probe/primary/data/root-icu77.bin) 为 **751,804 bytes**，SHA256 为：

```text
7aefc773d90fc2006c236720cd4e9220720efb33c7b8274ffeb24b494de3034e
```

[generate.py](../../tools/icu-probe/primary/export/generate.py) 核验相关 26 个源文件 / 数据文件与已验证发行 archive 的原始内容，检查安装库身份，再启动两个独立 exporter 进程。两次 binary 和 runtime metadata 完全一致，独立 Python parser 也通过 ranges、版本、表长度、context defaults 与 EOF 检查。统一验收再次运行 `--check`，生成结果与已跟踪数据完全一致。[本次生成 manifest](assets/icu77-cloud/primary/data-generation-manifest.json)、[数据身份与来源](../../tools/icu-probe/primary/data/root-icu77.json)

导出的实际 root PRIMARY options 是 `0x10`，`variableTop=0x0bffffff`，`numericPrimary=0x10000000`。Normalization、numeric、case level、case first、French secondary 均为 OFF，alternate 为 NON_IGNORABLE，reordering 为空；只把 strength 设为 PRIMARY。完整 canonical closure 继续保存在原版 ICU 数据中，FCD16 的 leading / trailing combining class 用于 contraction 阻塞判断，**没有对输入统一 NFD、重排或换成 ICU4X 的精简 collation 数据**。[实际 settings](../../tools/icu-probe/primary/data/root-icu77.json)

### 排序元素迭代、压缩与 Boost 包装

实现分为三个内部层，公开研究入口位于 [lib.rs](../../tools/icu-probe/primary/rust/src/lib.rs)：

| 层 | 实际实现内容 |
| --- | --- |
| [data77.rs](../../tools/icu-probe/primary/rust/src/data77.rs) | 校验固定格式与 settings；查询 CE32 / FCD16；加载完整 expansion、Jamo、compression 和 context 数据 |
| [ce77.rs](../../tools/icu-probe/primary/rust/src/ce77.rs) | 普通 forward 迭代；simple / long CE、Latin expansion、CE32 / CE64 expansion、prefix、最长 contraction、discontiguous contraction、跳过组合符的缓冲、numeric OFF digit、NUL、Hangul、offset 和 implicit primary、结束 sentinel |
| [key77.rs](../../tools/icu-probe/primary/rust/src/key77.rs) | ICU PRIMARY lead-byte 压缩、跨 primary 区间的 `03` / `ff` 标记、U+FFFE merge 与结束边界、终止零，以及 Boost 返回序列包装 |

Rust 的码点 cursor 与 context node ID 取代 ICU 的 UTF-16 指针和 packed trie state，但保留原算法的输入次序、最后已匹配节点、失败回退、被跳过组合符的后续处理，以及 prefix 对真实前文的查询。补充平面字符在解码后以完整码点参与匹配；完整 CE64 权重在 PRIMARY 编码前保留。对原型涉及的控制流进行了固定 ICU77 源码复核，并用完整 CE64 差分检查 PRIMARY 自身可能掩盖的迭代错误。[CE 诊断源码](../../tools/icu-probe/primary/export/trace-root.cpp)、[Rust trace 回归](../../tools/icu-probe/primary/rust/tests/root_primary.rs)

PRIMARY 压缩使用原版 `compressibleBytes` 全表；相同可压缩 lead byte 的后继权重按 ICU77 规则省略 lead，跨区间时根据方向写压缩结束标记，在 merge / 全键结束时遵守特殊边界。它不是把所有非零 primary 权重直接按大端拼接。Boost 包装随后把**每一个字节提升成一个 u32 元素**，不是四字节打包；仅当键总长大于 1 时去掉末尾终止零，因此全忽略输入与空串的 `[0]` 保留。[键实现](../../tools/icu-probe/primary/rust/src/key77.rs)、[实际原版 Boost 对照程序](../../tools/icu-probe/primary/oracle.cpp)

### 原型运行时边界

新 crate 的 Cargo 依赖数为 **0**，没有 `build.rs`、FFI、参考程序调用或运行时 ICU 数据服务。CLI 嵌入已跟踪的静态二进制数据；`--data` 可以选择重新生成的同格式文件。正式候选进程运行时撤去 `LD_LIBRARY_PATH`，并把 `ICU_DATA` 指向不存在的目录；独立 CLI 集成测试还用清空环境的子进程验证了内嵌数据与逐行错误处理。[Cargo.toml](../../tools/icu-probe/primary/rust/Cargo.toml)、[CLI 集成测试](../../tools/icu-probe/primary/rust/tests/cli.rs)、[PRIMARY 运行身份](assets/icu77-cloud/primary/summary.json)

实际 `ldd` 仅列出系统加载器、`libc` 和 `libgcc_s`，没有 ICU、Boost 或 `libstdc++`。这些库身份检查与零 Cargo 依赖共同支持本轮纯 Rust 排序计算的运行边界，不要求 Rust 可执行文件脱离操作系统运行。[实际 linkage](assets/icu77-cloud/primary/validation/primary-ldd.txt)

## 5. 验收范围与实际结果

### 主验收：两种完整序列都相等

每条合法输入先由开发期参考生成 **包含终止零的原始 ICU bytes**，并实际调用 Boost `transform_primary` 生成其暴露的完整 u32 序列。候选分别输出两列，比较器检查长度与每个元素；只有两列都相等才计入 `passed`。因此包装错误与排序元素 / 编码错误可以分别定位，不能仅以排序符号相等通过。[oracle.cpp](../../tools/icu-probe/primary/oracle.cpp)、[compare.py](../../tools/icu-probe/primary/compare.py)

| 集合 | 输入记录 | 合法完整键通过 | 按预期拒绝 | 差异 / 未支持 / 参考错误 |
| --- | ---: | ---: | ---: | --- |
| Directed，含原有两组语料 | 12,062 | 12,062 | 0 | 0 / 0 / 0 |
| SplitMix64 固定种子生成 | 20,000 | 20,000 | 0 | 0 / 0 / 0 |
| 全部 root context 的定向变体 | 16,046 | 16,046 | 0 | 0 / 0 / 0 |
| UTF-32 入口边界 | 10 | 4 | 6 | 0 / 0 / 0 |
| UTF-16 入口边界 | 10 | 5 | 5 | 0 / 0 / 0 |
| 全 Unicode scalar 单字符 | 1,112,064 | 1,112,064 | 0 | 0 / 0 / 0 |
| **合计** | **1,160,192** | **1,160,181** | **11** | **0 / 0 / 0** |

来源：[总汇总](assets/icu77-cloud/primary/summary.json)、[directed](assets/icu77-cloud/primary/directed/summary.json)、[generated](assets/icu77-cloud/primary/generated/summary.json)、[contexts](assets/icu77-cloud/primary/contexts/summary.json)、[u32](assets/icu77-cloud/primary/u32/summary.json)、[u16](assets/icu77-cloud/primary/u16/summary.json)、[all-scalars](assets/icu77-cloud/primary/all-scalars/summary.json)。

Directed 的 12,062 条记录包括原有 24 条、非 FCD 13 条、新增 28 条显式边界、700 条组合字符序列、125 条长输入，以及 11,172 个 Hangul 音节对应的分解 Jamo 序列。预组 Hangul 音节本身全部在 scalar sweep 中验证。显式边界涵盖 ASCII、Latin-1、空串、多个或夹在首尾的 NUL、primary ignorables、Han / radicals / compatibility characters、补充平面、未指派码点、U+FFFE / U+FFFF、expansion、prefix 与不同方向的 primary 压缩。[语料生成源码](../../tools/icu-probe/primary/generate_cases.py)、[directed 分类统计](assets/icu77-cloud/primary/directed/summary.json)

生成测试固定算法 **SplitMix64** 和种子 **`0x0042494355373701`**。20,000 条输入混合全域 scalar 抽样、脚本 / 组合符字符池及边界字符池；没有查询宿主 Python Unicode 数据库，也不根据参考输出调整答案。全部输入可由源码和种子再生成。[生成身份](assets/icu77-cloud/primary/cases/generation.json)

### Context、阻塞与真实失败路径

Context 语料来自完整导出数据的 78 个触发码点、77 个 trie 和 1,147 个 entry，并递归处理嵌套 context。计入触发路径后有 1,149 条基础路径；每条既验证成功路径，也修改真正参与匹配的 prefix 或 suffix。最终 **16,046 条**的组成如下：[context 分类统计](assets/icu77-cloud/primary/contexts/summary.json)

| Context 变体 | 记录数 |
| --- | ---: |
| 基础匹配路径 | 1,149 |
| 前后加入普通字符 | 1,149 |
| 实际匹配序列截断 | 1,149 |
| 实际匹配序列分叉 | 1,149 |
| 插入单个组合符、NUL 或 ZWJ | 8,015 |
| 插入多个可能阻塞 / 可跳过的组合符 | 3,435 |

截断不是向一个已经完成的 contraction 后面附加尾巴：suffix 路径删除最后一个必要码点，prefix 路径删除最远的必要前文；分叉则替换相应的必要码点。这让最长匹配、部分匹配失败、回退、阻塞和 discontiguous 匹配都得到实际输入覆盖。相应行为仍受有限 context 变体数量限制，不构成所有任意长组合的证明。[生成器的 contexts 路径](../../tools/icu-probe/primary/generate_cases.py)

完整 CE64 审计分别覆盖 directed **12,062 / 12,062** 和最终 contexts **16,046 / 16,046**，全部相等，0 差异 / 未支持 / 参考错误。审计包括零 primary 的 CE 和结束 sentinel，且使用与主键验收相同身份的 Rust 二进制。它增加对迭代忠实性的证据，仍未实现后续强度的 writer。[directed CE 审计](assets/icu77-cloud/primary/ce-audit-final-directed/summary.json)、[contexts CE 审计](assets/icu77-cloud/primary/ce-audit-final-contexts/summary.json)

### 压缩、长键与缓冲区边界

本轮观察到的原始 ICU 键长为 **1 至 30,001 bytes**，长度包含最后的 `00`。在完整验收集合中，键长恰为 **99 / 100 / 101 bytes** 的记录分别有 **31 / 24 / 37 条**：directed 提供 2 / 3 / 2 条，固定种子生成提供 29 / 21 / 35 条。它们实际调用 Boost，因此覆盖其 100-byte 局部键缓冲区两侧的结果一致性；更长输入验证了扩容后完整返回，没有用截断结果通过比较。[directed 长度统计](assets/icu77-cloud/primary/directed/summary.json)、[generated 长度统计](assets/icu77-cloud/primary/generated/summary.json)

这里的 PRIMARY 压缩是 lead-byte 压缩；secondary / tertiary 等级的 common-weight run 编码没有纳入实现。长输入覆盖多个长度、重复可压缩权重、Han、忽略字符及长组合序列，不是所有长度或所有 common-run 阈值的全强度验收。[PRIMARY writer](../../tools/icu-probe/primary/rust/src/key77.rs)、[长键测试](../../tools/icu-probe/primary/rust/tests/root_primary.rs)

辅助顺序检查分别有 directed 12,061、generated 19,999、contexts 16,045 对，总计 **48,105 对**，全部与同 settings 的 ICU 比较符号一致。它们是输入顺序中的相邻对，不是这些集合的全对全组合；也没有替代完整键对照。

### UTF-8、UTF-32、UTF-16 与原始 ICU 诊断

| 输入入口 | 本轮语义 | 非法值处理 |
| --- | --- | --- |
| UTF-8 | 接受合法 UTF-8；空串与 NUL 有效，保留原组合符顺序 | CLI 将非法编码报告为 `INVALID_UTF8`；错误行不当作键 |
| UTF-32 | 接受 Unicode scalar；按 Boost 经检查的 u32→u16 输入域进入排序 | surrogate 码点、超过 U+10FFFF 的值报告 `INVALID_UTF32`；本轮 6 条按预期拒绝 |
| UTF-16 检查适配器 | 有效 surrogate pair 解码后送入 Boost 的 u32 参考路径 | 未配对或顺序错误的 surrogate 报告 `INVALID_UTF16`；本轮 5 条按预期拒绝 |
| 显式 `--icu-utf16-only` | 仅用于直接 ICU 输入域诊断，保留未配对 UTF-16 单元的原值 | 不把 surrogate 改为 U+FFFD，也不把这个入口计为 Boost 对非法输入的接受 |

UTF-32 中写入两个 surrogate 数值并不等于提供一个有效 UTF-16 pair；前者仍按 Boost 的 UTF-32 检查拒绝。九字段字符分类对 surrogate 的既有 identity 策略，也不能推导排序入口必须接受同一值。上表保持输入域和诊断入口的区别，没有为方便原型改变已确认语义。位置检查使用原输入单元，trace 的 `input_position_cp` 则明确是内部诊断 cursor，不能当成正则匹配偏移。[输入接口与错误](../../tools/icu-probe/primary/rust/src/lib.rs)、[CLI 说明](../../tools/icu-probe/primary/rust/README.md)、[输入边界测试](../../tools/icu-probe/primary/rust/tests/root_primary.rs)、[ADR-0004](../adr/0004-rust-api-and-input-positions.md)

## 6. 可复现命令与证据位置

### 从干净 checkout 运行完整阶段

本轮实测的 Linux x86-64 环境需要可用的 C/C++ 构建工具、GNU Make、curl、Python 3.12 或更新版本，以及获取官方发行包 / Cargo 锁定依赖的网络。默认入口会把记录的官方 stable 工具链安装在项目目录，无需预先全局安装 ICU、Boost 或 Rust；Ubuntu 构建前提与完整参数见 [云端入口说明](../../tools/icu-probe/cloud/README.md)。

```sh
git clone --branch work/root-primary-cloud https://github.com/1298345095/BoostRegexRS.git
cd BoostRegexRS
python3 -B tools/icu-probe/cloud/run.py --jobs 6
```

统一入口依次准备官方依赖和工具链，构建并运行 Linux 参考，重新生成缺失的码点数据，重放旧候选与历史证据，重新导出并 `--check` 固定 root 数据，构建并运行 Rust PRIMARY 全套输入、全 scalar、CE64 审计，最后执行测试、format、Clippy、依赖和 linkage 检查。[统一 runner](../../tools/icu-probe/cloud/run.py)

默认结果位于 `target/research/icu77-cloud`。再次形成独立证据时可使用新的 cache / snapshot 目录，避免覆盖已有运行：

```sh
python3 -B tools/icu-probe/cloud/run.py \
  --cache target/research/icu77-cloud-recheck \
  --jobs 6 \
  --snapshot target/research/icu77-cloud-recheck/evidence
```

如果调用环境已经通过 rustup 安装 stable，可显式用 `rustup run stable python3 -B tools/icu-probe/cloud/run.py --system-rust --jobs 6`，runner 会记录该次实际工具链。`--skip-all-scalars` 只用于缩短诊断，输出会标记 `diagnostic_without_scalar_sweep` / `diagnostic_passed`，不能重用本报告的全 scalar 完成声明。完整运行返回 0 代表本轮阶段通过；已知历史 IDENTICAL 差异与空串参考错误仍分别保存，不因总入口为 0 而消失。

### 单独复验数据和运行 Rust

准备好默认云端环境后，单独复验固定数据：

```sh
python3 -B tools/icu-probe/primary/export/generate.py --check
```

运行已经构建的候选不需要 ICU 运行环境：

```sh
env -u LD_LIBRARY_PATH ICU_DATA=/nonexistent/icu-data \
  target/research/icu77-cloud/build/primary/release/icu77-root-primary \
  < tools/icu-probe/reference/cases.tsv
```

输出列为 `case_id`、包含末尾零的 `raw_icu_hex`、完整 `boost_u32_hex`。`--trace` 将 CE64、CE32 路径和键写入独立 stderr JSON，不改变 stdout 键协议。单独从 stable 构建与测试的命令见 [Rust 原型说明](../../tools/icu-probe/primary/rust/README.md)。

### 小型快照与可再生的大型证据

| 证据 | 仓库内位置 |
| --- | --- |
| Windows 原始证据 | [assets/icu-probe](assets/icu-probe/) |
| Linux 来源 / 构建 / 参考 / 旧候选重放 | [assets/icu77-cloud](assets/icu77-cloud/) |
| 本轮最终 stage、分组结果和生成身份 | [assets/icu77-cloud/primary](assets/icu77-cloud/primary/) |
| 固定 Rust 运行数据、格式与许可 | [tools/icu-probe/primary/data](../../tools/icu-probe/primary/data/) |
| 可审阅的代表性输入、参考与候选完整键 | [sample-cases.tsv](assets/icu77-cloud/primary/sample-cases.tsv)、[sample-reference.tsv](assets/icu77-cloud/primary/sample-reference.tsv)、[sample-candidate.tsv](assets/icu77-cloud/primary/sample-candidate.tsv) |
| 本轮快照文件摘要 | [snapshot-manifest.json](assets/icu77-cloud/primary/snapshot-manifest.json) |

下载包、编译产物、重新生成的 `codepoints.bin`、全部 scalar / generated / context 输入与完整输出，以及大型 CE trace 保留在 `target/research/icu77-cloud`。分组 JSON 记录了实际输入、参考和候选的 SHA256；CE 审计还记录 trace 文件大小与摘要。干净 checkout 不依赖这些未跟踪缓存，而是重新运行参考和生成器取得它们。小型摘要用于定位和核对运行身份，不能代替重放完整输入。

## 7. 构建、测试与检查

统一入口完成了以下实际检查；详细日志在 [validation 快照](assets/icu77-cloud/primary/validation/)，日志身份也包含在 [统一结果](assets/icu77-cloud/primary/cloud-summary.json) 中。

| 检查 | 实际结果 |
| --- | --- |
| 旧排序比较器 Python 回归 | 8 tests 通过 |
| PRIMARY 比较 / 参考进程 Python 回归 | 15 tests 通过 |
| Python 合计 | **23 tests 通过** |
| Rust PRIMARY | **10 tests 通过**：9 个算法 / 数据 / 边界测试和 1 个独立 CLI 子进程测试 |
| 根 crate | 1 个既有骨架测试通过 |
| 旧 ICU4X 候选 `cargo test` | 命令通过，0 个内置测试；实际验收来自外部重放 |
| 两个研究 crate `cargo fmt -- --check` | 通过 |
| 两个研究 crate `cargo clippy --all-targets -- -D warnings` | 通过 |
| C++ 数据导出 / CE trace 编译 | C++17、`-Wall -Wextra -Werror` 通过 |
| 重复数据导出与 `--check` | 通过 |
| 零 Cargo 依赖、运行环境隔离、`ldd` | 通过 |
| `git diff --check` | 通过 |

根 crate 原有名称 `BoostRegexRS` 仍产生 `non_snake_case` 警告；本轮没有为消除该既有警告而改名公开 crate。新的研究 crate 在上述 `-D warnings` Clippy 条件下通过。测试名称、原始输出和运行命令均保存，不能把根 crate 的一个骨架测试理解成正则引擎测试已经完成。[根测试日志](assets/icu77-cloud/primary/validation/root-tests.log)、[PRIMARY 测试日志](assets/icu77-cloud/primary/validation/primary-tests.log)

## 8. 结论边界与剩余工作

本轮填补了交接时最关键的两个缺口：可重复的官方云端参考环境，以及按输入实际计算、完整键逐元素通过记录语料的纯 Rust root PRIMARY 原型。全 scalar 单字符覆盖、完整 context 数据驱动测试、非 FCD CE 诊断和固定种子输入共同支持当前实现；它们仍然是有限输入与长度的验证，**不证明任意字符串已经穷尽**。

后续按照既定 [完整排序键路线](sort-key-implementation-plan.md) 推进：

1. **root IDENTICAL。** 实现 secondary、case、tertiary、quaternary 的 writer，以及 IDENTICAL 的 NFD / BOCSU 尾级；修复并逐完整键验收现有 root 18 对差异，继续保留默认非 FCD 行为，按 ADR-0005 验证空串例外。
2. **多 locale 与实际 settings。** 加入完整 tailoring、别名 / 回退、reordering、normalization ON 的 FCD 路径、numeric 和其它默认设置；先重放已有十 locale，再扩展完整 ICU77 locale / collation type，而不是把十个代表 locale 当成永久支持范围。145 对历史 IDENTICAL 差异是这一系列后续工作的回归集合。
3. **原型模块的生产化边界。** 当前代码在载入时构建查询表示，按输入缓冲码点与完整 CEs；应在功能证据基础上确定稳定模块接口、资源计量、内存与吞吐改进。现有结果没有给出满足最终性能门槛的结论。
4. **完整 Boost.Regex 行为与六平台验收。** 根库的语法、匹配、捕获、替换、错误和资源契约，以及 Windows / Linux / macOS 的六个架构组合仍需独立实现和测试。本轮 Linux 容器结果与 Windows 历史键核对，不等于六平台 Rust 库验收。
5. **`librime-rs` 接入继续暂缓。** 只有独立库达到既定完整验收之后，再恢复实际替换工作。

这些剩余项目没有作为 PRIMARY 的兼容例外获得豁免，也没有因本轮通过而放宽 [ADR-0003](../adr/0003-resource-contract-and-release-acceptance.md) 的首版完整功能、性能和内存门槛。
