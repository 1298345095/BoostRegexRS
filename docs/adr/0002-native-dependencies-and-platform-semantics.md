# 保留平台语义并移除 C/C++ 库依赖

为了让 Rust 程序直接使用本库，库实现不依赖 C/C++ 库，但允许调用操作系统 API，包括用于复现平台字符分类的 API。这一边界也适用于 Unicode 支持：需要提供 Boost.Regex 对应的能力，不能以依赖 ICU C/C++ 库作为最终库实现的解决方式。

首次完整验收覆盖以下六个目标组合：Windows x86-64 / ARM64（MSVC），Linux x86-64 / ARM64（glibc），macOS x86-64 / ARM64。32 位、Windows GNU 与 Linux musl 不纳入首版支持承诺。在相同平台和约定运行条件下对照 Boost.Regex 1.89.0；若上游行为随平台而异，分别兼容各自平台，不强制统一结果。

Unicode 对照固定 ICU4C 77.1、Unicode 16.0.0、CLDR 47，使用原版完整 ICU 数据。Rust 实现对齐该组行为，后续数据升级显式进行；Rust 工具链更新不自动改变字符数据版本。ICU4X 2.0 仅作为候选验证对象，不因数据版本一致就认定行为兼容或选为生产依赖。

首版系统验证基线为 Windows Server 2025 x86-64、Windows 11 ARM64、Ubuntu 24.04 LTS x86-64 / ARM64、macOS 15 Intel / Apple Silicon。本地 Windows 11 x86-64 测量为补充。每次验证记录实际系统与镜像、运行时、编译器及数据版本；基线的选择不代表这些环境已经通过测试，也不等于对全部更旧系统的承诺。

优先建立独立字符规则与排序键对照探针，再确定最终 Rust 依赖和实现方式。完整 locale、别名、数据回退及排序键的逐项矩阵继续按上游公开能力细化，不能用代表性 locale 集合缩小支持范围。

测试工具允许构建和运行 C++ Boost / ICU 参考程序。发布的 Rust 库仍遵守不依赖 C/C++ 库、允许操作系统 API 的约定。

ICU locale 查询保留原版行为；空串排序采用确定的有效键并列为明确兼容例外，详见 [ADR-0005](0005-icu-locale-query-and-empty-sort-key.md)。

Rust 工具链跟随 stable，不额外承诺固定的历史最低支持版本。验证使用 stable；为使对照和性能结果可复查，记录每次验证实际使用的工具链版本，而不以此固定长期支持下限。
