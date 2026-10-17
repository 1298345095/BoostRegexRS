# ICU / Unicode 兼容基准调查与方案

日期：2026-10-17。本文为前期研究记录；Q27 已确认 ICU77.1 / Unicode16.0.0 / CLDR47，并授权继续对照探针，见 ADR-0002。以下源码调查不等于运行验证，候选依赖尚未认定为生产实现；后续运行结果见 [ICU 探针实测](icu-probe-results.md)，完整排序键和名称对照仍未完成。

## 建议固定的组合

| 项目 | 建议基准 | 固定位置 |
|---|---|---|
| 正则语义 | 官方 Boost.Regex 1.89.0 | `boost-1.89.0` |
| ICU4C 参考实现 | 77.1，原版完整数据 | [`release-77-1`](https://github.com/unicode-org/icu/releases/tag/release-77-1) |
| Unicode / UCD | 16.0.0 | [版本化 UCD 目录](https://www.unicode.org/Public/16.0.0/ucd/) |
| locale 数据 | CLDR 47 | [`release-47`](https://github.com/unicode-org/cldr/releases/tag/release-47)；ICU 自带生成数据为实际参考 |
| 首轮 Rust 候选 | ICU4X 2.0.0 的 casemap / properties / collator | [`icu@2.0.0`](https://github.com/unicode-org/icu4x/releases/tag/icu@2.0.0)，只作可行性验证 |

这是为可复现性选择的已发布组合，不声称它是调查当日最新版本。官方 ICU 77 发布页确认 77.1 的发行、CLDR 47 来源及三类桌面系统测试；该 tag 的 `uchar.h` 指定 Unicode 16.0。ICU4X 2.0 发布说明同样明确其编译数据是 CLDR 47.0 / Unicode 16.0，因此适合先做版本对齐的探针。两者版本对齐不构成行为等价证明。[ICU 77 发布页](https://unicode-org.github.io/icu/download/77.html)、[ICU 77.1 Unicode 声明](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/uchar.h#L49)、[ICU4X 2.0 发布说明](https://github.com/unicode-org/icu4x/releases/tag/icu@2.0.0)。

参考程序应显式加载此版完整 ICU 数据，不取机器预装 ICU 或持续更新的维护分支。基准建立时记录完整 commit、下载包 SHA-256、数据包 SHA-256、编译器和选项；目前未下载这些材料，因此不填写猜测的哈希。启动时核对实际 `u_getVersion` / `u_getUnicodeVersion`、CLDR 数据版本及 collator 版本，连同请求、实际有效 locale 一起写入结果。固定库代码和数据同样必要：ICU 自身说明 collation runtime / builder 版本会影响键和排序元素。[ICU 77.1 版本与排序版本定义](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/uvernum.h#L139)。

## 已核查的 Boost 能力边界

主证据是本地官方源码 [boost/regex/v5/icu.hpp](D:/NewProgram/librime-rs/target/regex-oracle-cache/boost_1_89_0/boost/regex/v5/icu.hpp:44)，对应上游 [`boost-1.89.0` 源码](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/icu.hpp)。下述行号均指本地文件。

| Boost 入口 | 实际行为 | Rust 侧必须保留的部分 |
|---|---|---|
| `translate_nocase`，164 | `u_foldCase(c, U_FOLD_CASE_DEFAULT)` | 逐码点简单折叠，不可替换为会扩展字符串的 full folding |
| `tolower` / `toupper`，172 | `u_tolower` / `u_toupper` | 逐码点映射；ICU locale 不使此入口变成土耳其语字符串大小写转换 |
| `transform` / `transform_primary`，52、70、180 | 为 locale 建立 IDENTICAL / PRIMARY 两个 collator，经 UTF-16 获取 sort key | 保留两种强度、locale 默认选项、编码与结果序列 |
| `lookup_classname`，188；`lookup_icu_mask`，368 | Boost 内置类，加硬编码 General_Category 及 `any/ascii/assigned` 等名称表；再按 Boost 代码规范化名称 | 保留接受与拒绝集合；不能把 ICU4X 的所有属性别名自动开放为 Boost 兼容行为 |
| `lookup_collatename`，260 | ASCII 名称依次尝试 ICU Unicode 名、extended 名、Boost POSIX 名；最后还有单字符回退 | 保留名称优先级、算法名称、合成 extended 名以及无效名称行为 |
| `isctype` / `value`，290、331 | General_Category 掩码与 Boost 特例，调用 `u_isblank`、`u_isspace`、`u_digit` 等 | 不能直接替换成 Rust 标准字符谓词 |

源码没有通过通用 ICU UnicodeSet 解析所有 Script / Block / 二进制属性，也没有调用 ICU 的正则引擎、日期格式化等其他服务。因此“ICU 支持完整移植”应覆盖 Boost 公开使用的能力；全面重写 ICU 本身不由这项需求推出。

具体容易误用的地方：ICU `u_isspace` 在分隔符之外还包含 U+001C–U+001F；`u_digit` 支持十进制数字以及 ASCII / 全角拉丁字母的进制值。这些行为与泛称的 Unicode whitespace / ASCII digit 并非同一个契约。应按固定 ICU 源码重现并逐码点对照。[ICU 77.1 `uchar.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/uchar.cpp#L183)。

排序键是独立验收项：`do_transform` 把键字节提升为 `UChar32` 序列，通常去掉末尾 NUL，但当键长度为 1 时保留该值（70–95）。只证明两段文本的比较顺序相同，不能证明该公开 traits 输出相同；默认按输出序列逐项相等验收。若未来希望只承诺顺序或匹配结果等价，需要另行形成可观察行为差异决策，不能在依赖选型中默默放宽。

## 纯 Rust 候选与缺口

| 部分 | 已有候选证据 | 提案及尚未证明的内容 |
|---|---|---|
| simple lower / upper / fold | ICU4X 2.0 `CaseMapperBorrowed` 明确提供逐字符 simple 方法 | 优先验证；先对所有 Unicode scalar values 对照 ICU。代理码点等不能放进 Rust `char` 的值须独立处理 |
| General_Category | ICU4X 2.0 提供 `GeneralCategory` 与 group；其 group 位值对应 ICU4C mask | 用版本固定的数据，Boost 自身的名称表和复合类仍由适配层实现 |
| ICU 特殊谓词、数字值 | 能从固定 UCD 加少量规则提供 | 以 ICU77.1 为判据；不要以 `char::is_whitespace` 等代替后直接宣称兼容 |
| PRIMARY / IDENTICAL 排序 | ICU4X 2.0 提供 locale-aware compare 和两种强度；检查其导出与 comparison 实现，没有 sort-key 输出 API | 同版数据可用于排序候选验证，但不足以实现完整公开 `transform`；键编码需补充固定版本 Rust 实现 |
| 字符名称反查 | 本次未找到 ICU4X 2.0 提供等价 `u_charFromName` 的公开入口；properties 的 names 模块用于属性名称 | 提议从固定 UCD 生成名称索引，并实现 ICU77.1 的算法 / extended 名称规则与接受条件；这仍是一项实际开发工作 |

逐字符 API 证据见 [ICU4X 2.0 casemapper.rs](https://github.com/unicode-org/icu4x/blob/icu@2.0.0/components/casemap/src/casemapper.rs#L447)；类别与 mask 见 [ICU4X 2.0 props.rs](https://github.com/unicode-org/icu4x/blob/icu@2.0.0/components/properties/src/props.rs#L195)；属性名称公开导出见 [ICU4X 2.0 properties/lib.rs](https://github.com/unicode-org/icu4x/blob/icu@2.0.0/components/properties/src/lib.rs#L70)；排序入口与实现见 [collator/lib.rs](https://github.com/unicode-org/icu4x/blob/icu@2.0.0/components/collator/src/lib.rs#L306)、[comparison.rs](https://github.com/unicode-org/icu4x/blob/icu@2.0.0/components/collator/src/comparison.rs#L487)。

名称数据不能只收录 UnicodeData 中显式 Name 字段而漏掉 Hangul / CJK 等算法名称或 ICU 合成名。ICU 的 extended 路径还验证名称中的类别和十六进制码点；反查实现会转换 ASCII 大小写。应从该版源代码和固定数据导出精确规则，不用通用“宽松名称查找”替代。普通名称与 extended 名称的调用选择也应维持 Boost 的先后顺序。[ICU77.1 `unames.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unames.cpp#L1414)、[Unicode16.0 UCD](https://www.unicode.org/Public/16.0.0/ucd/)。

ICU4X 2.0 是优先调查对象，尚未选为生产依赖。可替代路径是从同版 [UnicodeData.txt](https://www.unicode.org/Public/16.0.0/ucd/UnicodeData.txt) 与 [CaseFolding.txt](https://www.unicode.org/Public/16.0.0/ucd/CaseFolding.txt) 生成紧凑的 Rust 分类 / simple case 表，所需 folding 使用 C+S 规则。这样能固定数据而不随 stable Rust 更新改变语义。完整 locale collation 仍需算法与 tailoring 数据，不能靠静态单字符分类表补齐。

## 建议的落地顺序与验收产物

1. 建立独立 traits 探针：C++ 侧只有官方 Boost1.89 + ICU77.1；Rust 侧只验证字符规则、名称、排序，先不依赖正则引擎是否完成。
2. 全量码点对照：覆盖 0..0x10FFFF，包括代理码点和未分配点，分别验证类别、空白、数字、大小写；无效范围与负值按各入口可观察行为单列，不将其强制转换为有效 `char`。补充全部 Boost 名称表及大小写 / 连字符 / 下划线 / 空白变体、无效别名。
3. 名称对照：全量显式及算法名称正反查，再覆盖 extended 类别名称、大小写、边界码点、错误类别和不存在的名称；验证 Boost POSIX 与单字符回退。名称 API 是否接受嵌入 NUL 由实际 Boost 指针范围转 `c_str` 的行为测定。
4. 排序对照：先 root、en_US、tr_TR、de_DE、sv_SE、fr_CA、es_ES@collation=traditional、zh_CN、ja_JP、th_TH，分别测试 PRIMARY / IDENTICAL；包含组合 / 预组字符、重音、假名、数字、收缩、多码点扩展、空串、NUL、长键、补充平面。比较顺序、键完整序列及使用这些键的正则结果分开记录。
5. locale 完整性：上述是快速暴露差异的固定语料集，不是只支持这些 locale。完整验收从 ICU77.1 完整数据枚举可用 locale / collation 类型生成版本化清单；locale 别名、关键字、fallback、无效名称及未显式指定 locale 的默认值分别对照。默认 locale 来自环境的行为需要隔离进程环境测试，不把 root 替换为默认 locale。
6. 若 ICU4X 候选在公开键或某类 locale 行为上存在缺口，保留验收项，按 ICU77.1 固定数据与算法开发 Rust 等价实现，并保存所需许可证与来源。完成前不能宣称 ICU 全面兼容；不改用发布库 C/C++ 依赖绕开已确认的约束。

产物应包括参考环境锁定清单、逐入口差异清单、固定 locale 清单、复现用例及生成数据来源。以上步骤尚未执行；运行成本、数据体积、完整键兼容难度与进度都尚未测量，不能从“存在 ICU4X”推导出已解决。

## 待决策与已知限制

- 已确认固定 ICU77.1 / Unicode16.0.0 / CLDR47 为首版语义基准；以后升级数据需显式版本决策并重跑对照。它与跟随 stable Rust 工具链是两条独立版本线。
- `icu_regex_traits::getloc()` 在本地源码341返回默认 `locale_type()`，与其内部保存的 imbue locale 不同；属于应加入差异清单的上游可观察怪癖，按已确认的逐项决策处理，本文不预先修正或决定保留。
- 全面 locale 与键兼容是本方案最大的可行性工作，未获得实测证明。建议先完成上述 traits 探针，再冻结最终 Rust 依赖与估算；该顺序不降低完整交付要求。
