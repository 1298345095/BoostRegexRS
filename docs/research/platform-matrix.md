# 平台、工具链与 locale 验收方案

调查日期：2026-10-17。状态：**研究与建议，尚未执行六目标验收，也未配置或触发远程 CI。**

已确认的范围是 Windows x86-64 / ARM64（MSVC）、Linux x86-64 / ARM64（glibc）、macOS x86-64 / ARM64；Rust 跟随 stable；逐平台对照官方 Boost.Regex 1.89.0。这里提出实际验证环境，不把 Rust 自身的 OS 下限转换为本库已验证的支持下限，不改变现有支持承诺。

## 结论与建议

首个完整发布使用下列六个**原生运行**环境。采用明确 OS 标签，避免 `*-latest` 自动换代；每次运行仍须保存镜像版本，因为明确 OS 标签的内容也会更新。GitHub 官方当前列出这些标准 runner 及其架构。[GitHub runner 文档](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job)、[镜像更新规则](https://github.com/actions/runner-images/blob/main/README.md)

| Rust target | 建议 OS 验证基线 | 标准 runner 候选 | 参考程序工具链建议 | 当前状态 |
|---|---|---|---|---|
| `x86_64-pc-windows-msvc` | Windows Server 2025 x64 | `windows-2025` | 镜像中可用的 MSVC；保存 `cl /Bv` 与 SDK 版本 | 未执行 |
| `aarch64-pc-windows-msvc` | Windows 11 ARM64 | `windows-11-arm` | ARM64 MSVC；保存实际 VS / MSVC / SDK 版本 | 未执行 |
| `x86_64-unknown-linux-gnu` | Ubuntu 24.04 LTS x64 | `ubuntu-24.04` | GCC 13 / libstdc++；记录精确包版本 | 未执行 |
| `aarch64-unknown-linux-gnu` | Ubuntu 24.04 LTS ARM64 | `ubuntu-24.04-arm` | GCC 13 / libstdc++；记录精确包版本 | 未执行 |
| `x86_64-apple-darwin` | macOS 15 Intel | `macos-15-intel` | 镜像 Xcode 的 Apple Clang / libc++ / SDK | 未执行 |
| `aarch64-apple-darwin` | macOS 15 Apple Silicon | `macos-15` | 镜像 Xcode 的 Apple Clang / libc++ / SDK | 未执行 |

选择 Ubuntu 24.04 / macOS 15 是为获得可重复安排的成熟环境，不要求追逐最新 OS。Ubuntu 24.04 官方镜像说明列有 GCC 13、glibc locale 数据包；Windows ARM 镜像说明还包含工具链迁移公告，因此不能只凭 `windows-11-arm` 假设固定 VS 版本。[Ubuntu 镜像说明](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)、[Windows ARM 镜像说明](https://github.com/actions/runner-images/blob/main/images/windows/Windows11-Arm64-Readme.md)

GitHub 文档说明标准 runner 对公开仓库免费；私有仓库会消耗额度并可能按分钟收费。本次只读执行 `gh repo view 1298345095/BoostRegexRS --json visibility,viewerPermission` 确认仓库为 PUBLIC、当前查看者权限为 ADMIN；`gh api repos/1298345095/BoostRegexRS/actions/permissions` 返回 `enabled: true`、`allowed_actions: all`。**这些信息不证明六个 runner 已能实际调度；额度、runner 特定限制和实际执行仍未验证。** 方案不申请 larger runner、不开启付费资源；任一目标无法使用时，状态保持“未验证”，后续使用已授权的原生环境完成验证。[GitHub runner 可用性及计费规则](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job)

## Rust 官方要求与本库验证的区别

当前 Rust 官方资料给出的要求如下；它们会随 stable 变化，实际发布应附带当次快照。

- Windows MSVC：Windows 10+ 或 Windows Server 2016+；Visual Studio 最低 2017，但官方建议较新 VS。这不是本库已测试过 Windows 10 / Server 2016 的证据。[Rust Windows MSVC 要求](https://doc.rust-lang.org/rustc/platform-support/windows-msvc.html)
- Linux GNU：x64 为 kernel 3.2+ / glibc 2.17+；ARM64 为 kernel 4.1+ / glibc 2.17+。本方案使用 Ubuntu 24.04 作为实际参考环境，没有测试所有满足这些下限的发行版。[Rust 平台表](https://doc.rust-lang.org/rustc/platform-support.html)
- macOS：Rust 文档列 x64 10.12+、ARM64 11+；当前 x64 macOS 属于 Tier 2 with host tools，ARM64 属于 Tier 1。Rust 对 Tier 2 的构建承诺不能代替本库的原生运行测试。[Rust macOS 要求](https://doc.rust-lang.org/rustc/platform-support/apple-darwin.html)、[Rust tier 定义](https://doc.rust-lang.org/rustc/platform-support.html)

建议发布说明写明“在上述六组环境完成验证”，并列真实版本；较旧 OS 的运行兼容性作为后续可单独增加的验证维度。不要把设置低 deployment target、交叉编译通过、Rosetta / QEMU 成功运行，记作对应原生目标的完整验收。

工具链策略：日常 CI 解析当次 stable；一次完整验收启动时解析并记录同一个 stable 版本，六目标都使用该版本以便比较。若执行期间 stable 更新，不在一组结果里混用版本；下一组再跟进。记录版本不等于承诺历史 MSRV。参考 C++ 程序与 Rust 程序使用同一机器、同一 OS 数据和相同输入。

## locale 验证必须按 traits 后端分开

Boost 1.89 官方文档明确：非 Windows 默认使用 `std::locale`；可以选择 C locale 或 C++ locale，Windows 可禁用 Win32 后端。Win32 traits 源码调用 Windows 大小写、字符分类、排序和编码转换 API。因此“同一个语言名称”不意味着三个后端有相同结果。[Boost locale 配置](https://www.boost.org/doc/libs/1_89_0/libs/regex/doc/html/boost_regex/configuration/locale.html)、[Boost 1.89 Win32 traits 源码](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/w32_regex_traits.hpp)

建议验收报告为以下后端分别建条目：

1. Windows 默认 Win32 traits：显式 LCID、窄字节和 UTF-16 宽字符；额外记录默认 locale 路径。
2. 各平台 C++ locale traits：C / classic 及具名 locale，分 `char` 和 `wchar_t`。Linux 固定 libstdc++，macOS 固定 libc++，Windows 固定 MSVC STL。
3. C locale traits：覆盖公开能力清单中适用的全局 locale 路径；变更全局 locale 的测试进程隔离，避免互相污染。
4. ICU traits：使用另行固定的 ICU / Unicode / CLDR 数据基准，覆盖 UTF-8 / UTF-16 / UTF-32；locale ID 与平台具名 locale 分开记录。
5. 用户自定义 traits：用确定性测试对象验证扩展接口；不能依靠系统 locale 列表证明扩展机制正确。

### 建议的定向用例集

这是一组**必须测试的代表性 locale**，不将产品能力限定为这几个 locale。对具名 locale 的创建失败，分别记录“环境缺数据”“上游不支持该名称”“实现错误”，不允许默默退回 C locale 后计为通过。

| 语言 / 场景 | Windows NLS 名称（保存解析后 LCID） | POSIX 名称候选（先检查 `locale -a`） | ICU ID | 主要目的 |
|---|---|---|---|---|
| 基线 | Win32 后端单独测 invariant 和默认 LCID；C / C++ 后端测 `C` | `C`，Linux 额外测 `C.UTF-8` | `root` | 确定基线；不把 C、invariant、root 当成同一语义 |
| 美国英语 | `en-US` | `en_US.UTF-8` | `en_US` | 常规分类、大小写、标点、排序 |
| 土耳其语 | `tr-TR` | `tr_TR.UTF-8` | `tr_TR` | `I/i/İ/ı` 的实际 API 行为 |
| 德语 | `de-DE` | `de_DE.UTF-8` | `de_DE` | `ß/ẞ/SS`、变音、等价类 / 排序键 |
| 日语 | `ja-JP` | `ja_JP.UTF-8` | `ja_JP` | 平假名 / 片假名、半角 / 全角、窄编码边界 |
| 简体中文 | `zh-CN` | `zh_CN.UTF-8` | `zh_CN` | 汉字分类、标点、排序、窄编码边界 |
| 瑞典语补充 | `sv-SE` | `sv_SE.UTF-8` | `sv_SE` | `Å/Ä/Ö` 的语言排序差异 |

GNU 文档指出除 C / POSIX 外 locale 名称由系统决定；先发现实际名称再创建对象。Linux 可以在以后 CI 中由指定 glibc locale 源和 charmap 生成测试所需 locale，保存源数据版本与生成参数；本次没有生成或安装。[GNU locale 名称](https://sourceware.org/glibc/manual/latest/html_node/Locale-Names.html)、[locale 命令](https://man7.org/linux/man-pages/man1/locale.1.html)、[localedef 命令](https://man7.org/linux/man-pages/man1/localedef.1.html)

Windows 窄字符测试另建编码维度：英语 / 德语的 CP1252、土耳其语 CP1254、日语 CP932、简中 CP936，以及 UTF-8 代码页环境。**这些是用例输入编码与环境组合，不是假设 Win32 traits 提供任意 codepage 参数。** 保存请求 locale、实际 LCID、locale 默认 ANSI codepage、进程 ACP 及 UTF-8 manifest 状态；按 Boost 实际调用的 A/W API 与转换路径生成期望值。多字节文本的单字节分类、孤立前导字节、无效序列都要测试，不能把字节正则自动当成 Unicode 正则。系统 codepage 环境缺失时，标记未执行；不修改开发机全局区域设置。

C / C++ traits 的 `C` 与 Windows NLS invariant 分开对照。CRT 具名 locale 还可能包含 codepage；测试前必须检查创建是否成功并保存实际返回名称。[Microsoft CRT locale 命名](https://learn.microsoft.com/en-us/cpp/c-runtime-library/locale-names-languages-and-country-region-strings?view=msvc-170)、[setlocale 语义](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/setlocale-wsetlocale?view=msvc-170)

用例测试分类、单字符映射、匹配 / 捕获、locale 范围、等价类、排序键和输出。不能依据自然语言推断期望值：例如 Microsoft 文档说明 LCMapString 的土耳其语映射还受具体 flags 影响，NLS 版本也可能改变映射和排序。以固定 Boost 实测为裁判，并记录排序数据版本。[Windows 排序与映射](https://learn.microsoft.com/en-us/windows/win32/intl/handling-sorting-in-your-applications)

## CI 与发布验证的具体划分

建议每个提交的原生六目标作业运行：构建、单元测试、核心差分语料、全部上述定向 locale 的短用例、默认配置与完整配置验证。完整能力默认开放；仅在明确提供精简 feature 组合以后，增加这些组合的独立验证。

发布候选再在六目标运行：全部适用上游测试、完整差分语料、traits 定向覆盖、固定种子自动生成用例及既定模糊测试预算。编译与运行结果独立记录；编译成功但未运行仍为“未验证”。缺失 locale / runner / 参考构建不能成为静默跳过。公开 API 中存在而上游在特定环境不可用的组合，保留“环境不适用”说明及上游证据，不能给整个能力打通过。

性能测量使用各平台原生固定机器或同一作业内交替运行 Boost 与 Rust；普通共享 runner 结果用于发现退化，若方差超出约定阈值则在固定环境复测，不能用不同机器的绝对耗时直接作验收比例。具体工作负载及门槛由性能研究方案定义。

## 每次验收保存的环境清单

| 层次 | 必须保存的证据 / 取得方式建议 |
|---|---|
| 通用 | 仓库 commit、Cargo.lock、Boost 1.89.0 源码摘要、补丁状态、flags / 宏、参考程序摘要、语料摘要、测试种子、实际架构；`rustc -Vv`、`cargo -V`；runner `ImageOS` / `ImageVersion` / 构建日志与镜像说明的 commit |
| Windows | OS edition / build / UBR；`cl /Bv`、选用 SDK / VS 组件；加载的 UCRT / MSVC runtime 文件版本；每 locale 的实际 LCID / ANSI codepage、`GetACP`、默认 locale；用 `GetNLSVersionEx` 记录排序版本。Shell 的 `chcp` 不能代替 ACP 证据 |
| Linux | `/etc/os-release`、`uname`、`ldd --version`；`g++-13 -v`；实际 libstdc++ 路径与包版本；`dpkg-query` 记录 `libc6` / `locales` / `libstdc++6`；`locale -a`、`locale -k LC_CTYPE LC_COLLATE`；locale 源 / charmap 摘要和生成参数 |
| macOS | `sw_vers`、`uname`、Xcode build / `xcrun clang --version` / SDK 版本；实际 libc++ / 系统 dylib 标识；`locale -a` 及已选 locale 的真实创建结果；系统 locale 数据可读文件摘要 / OS build 作为版本依据，不用外部 ICU 版本替代系统 locale 版本 |
| ICU 参考环境 | ICU library version、Unicode version、CLDR version、collator version / UCA version、数据包摘要、构建选项、实际 locale / fallback locale；与系统 NLS / glibc / Darwin 数据单列 |

Windows 的 NLS 版本会影响排序，Microsoft 提供版本查询用于跟踪此类变化；因此保存 OS 名称还不够。[NLS 版本说明](https://learn.microsoft.com/en-us/windows/win32/intl/handling-sorting-in-your-applications)

## 尚待验证的具体事项

- 六个 runner 在本仓库的实际调度、原生架构和完整参考程序构建；仓库级 Actions 已启用，但六目标作业目前全部未执行。
- macOS 15 / Windows 当前镜像可创建的 locale 名称、平台 C++ traits 的真实接受范围，以及 UTF-8 codepage 环境的可重现方式。
- 发布时所选 stable 的实际目标要求、镜像软件版本，以及镜像退役前的替换验证流程。若标签退役，在替代环境重新执行完整矩阵，不把旧标签改名当成验收。
- 上述矩阵是验收环境建议；若需要对更旧 OS 作运行支持承诺，须增加实际原生环境及结果。当前不能声称完整跨系统验证已经完成。

文档查询路径：先 Context7 resolve / query（Rust、GitHub Actions、runner-images），再核对 Rust、GitHub、Boost、Microsoft、GNU 的官方页面与源码。动态资料以本次查询时内容为准，最终验收使用实际执行产生的环境清单。
