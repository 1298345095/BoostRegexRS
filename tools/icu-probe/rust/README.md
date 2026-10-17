# ICU4X 2.0 compatibility probe

This is an isolated research executable. It is not a production regex engine
or a dependency of the root package. All ICU4X components and compiled-data
crates are fixed to `=2.0.0`; `Cargo.lock` additionally pins their transitive
dependencies. Run with `--locked`. The target baseline is Unicode 16 / CLDR 47.

```powershell
$ErrorActionPreference = 'Stop'
$env:CARGO_TARGET_DIR = "$PWD/target/research/icu-probe/rust/build"
cargo +stable run --locked --release --manifest-path tools/icu-probe/rust/Cargo.toml -- `
  --reference target/research/icu-probe/reference/output/codepoints.bin `
  --summary target/research/icu-probe/rust/summary.json `
  --cases tools/icu-probe/reference/cases.tsv `
  --ordering-output target/research/icu-probe/rust/ordering.tsv
```

The reference file must have exactly 1,114,112 sequential records, each ten
little-endian u32 values: code point, simple lowercase, simple uppercase,
default simple fold, ICU general category number, blank, space, and `u_digit`
for radix 10 / 16 / 36. Negative digits use `FFFFFFFF`. Invalid file length or
code point order is rejected. The Rust candidate never constructs its answers
from the reference values.

`summary.json` keeps direct ICU4X results separate from the ICU compatibility
adapter. Direct simple case APIs accept `char`, so all 2,048 surrogate code
points are explicitly unsupported. The adapter uses unchanged code points for
these non-scalar values, consistent with default simple case mapping. Category
lookup uses `get32` and covers surrogates directly.

The direct binary `WhiteSpace` property differs from ICU `u_isspace` at
U+001C..U+001F. The adapter adds those four information separators. Blank uses
TAB or general category Zs. Decimal values use fixed Unicode 16 Nd runs as
ordered ten-digit sequences; all run lengths are validated as multiples of
ten before using this research-only adapter. Radices above ten additionally
recognize ASCII and fullwidth Latin letters. These rules follow ICU public
semantics, not values copied from the oracle:

- [ICU 77.1 character classification implementation](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/uchar.cpp)
- [ICU 77.1 u_digit contract](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/uchar.h)
- [Unicode 16 decimal digit properties](https://www.unicode.org/versions/Unicode16.0.0/core-spec/chapter-4/#G134153)
- [ICU4X 2.0 case mapper](https://docs.rs/icu_casemap/2.0.0/icu_casemap/struct.CaseMapperBorrowed.html)
- [ICU4X 2.0 general category](https://docs.rs/icu_properties/2.0.0/icu_properties/props/enum.GeneralCategory.html)

Ordering output contains each input-ordered distinct pair for each locale and
PRIMARY / IDENTICAL strength. `root` is explicitly mapped to BCP47 `und`,
`es_ES@collation=traditional` to `es-ES-u-co-trad`, and remaining locale IDs to
their corresponding BCP47 tags. Mapping is reported in the JSON. Constructor
failure yields `unsupported`; built-in ICU4X locale fallback remains library
behavior and is explicitly disclosed. Agreement on a finite pair corpus does
not establish locale identity or full collation compatibility.

ICU4X 2.0 exposes no public sort-key output API. This executable compares
ordering signs only and reports sort-key output as unsupported. It does not
manufacture compatible keys from comparisons.

The first build with current transitive dependencies exposed a missing
`zerofrom/alloc` feature for `Cow<str>` in the old case-map component; the
probe explicitly enables that feature. No crate source is patched. Toolchain
and dependency-tree evidence is saved under
`target/research/icu-probe/rust/{rustc.txt,cargo.txt,cargo-tree.txt}`.
