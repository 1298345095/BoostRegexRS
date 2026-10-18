# Native development reference and original test input adapter

The development reference uses official Boost.Regex 1.89.0 under the Boost
Software License 1.0, reproduced in `LICENSE_1_0.txt`.

`upstream_cases.cpp` adapts the narrow-character macros from
`libs/regex/test/regress/test.hpp` (Copyright (c) 2004 John Maddock). It includes
the original regression `.cpp` files from the verified Boost source archive
without editing them. Those files retain their original copyright headers in
that archive. Corpus provenance records their exact relative paths and SHA256.

The collector emits inputs and separately preserves the original test assertions.
The candidate receives only the input protocol and computes results through the
public pure Rust library. The native oracle and original expected outputs do not
become production dependencies or a known-input answer table.
