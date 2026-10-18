//! Canonical decomposition using only the fixed ICU77 / Unicode16 export.
//!
//! This normalization is used after CE iteration, for the IDENTICAL level.
//! It never changes the code points seen by the normalization-OFF CE iterator.

use crate::data77::Reader;
use crate::{Error, Result};

#[derive(Debug)]
struct Mapping {
    code_point: u32,
    decomposition: Vec<u32>,
}

#[derive(Debug)]
struct CombiningClassRange {
    end: u32,
    class: u8,
}

/// Immutable canonical decompositions and combining classes from ICU4C 77.1.
#[derive(Debug)]
pub struct NfdData77 {
    mappings: Vec<Mapping>,
    classes: Vec<CombiningClassRange>,
}

impl NfdData77 {
    /// Decode the documented BRSNFD77 schema, including its fixed data versions.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let mut reader = Reader::new(bytes);
        if reader.take(8)? != b"BRSNFD77" || reader.u32()? != 1 {
            return Err(Error::Data("unsupported NFD table magic/schema"));
        }
        for expected in [77, 1, 16, 0, 47, 0] {
            if reader.u32()? != expected {
                return Err(Error::Data("expected ICU 77.1 / Unicode 16.0 / CLDR 47.0"));
            }
        }
        let count = reader.count(8)?;
        let mut mappings: Vec<Mapping> = Vec::with_capacity(count);
        for _ in 0..count {
            let code_point = reader.u32()?;
            if !is_scalar(code_point)
                || mappings
                    .last()
                    .is_some_and(|entry| entry.code_point >= code_point)
            {
                return Err(Error::Data("NFD mappings must be strictly ordered scalars"));
            }
            let length = reader.count(4)?;
            if length == 0 {
                return Err(Error::Data("empty canonical decomposition"));
            }
            let mut decomposition = Vec::with_capacity(length);
            for _ in 0..length {
                let cp = reader.u32()?;
                if !is_scalar(cp) {
                    return Err(Error::Data("non-scalar canonical decomposition"));
                }
                decomposition.push(cp);
            }
            mappings.push(Mapping {
                code_point,
                decomposition,
            });
        }
        let count = reader.count(5)?;
        let mut classes: Vec<CombiningClassRange> = Vec::with_capacity(count);
        for _ in 0..count {
            let end = reader.u32()?;
            let class = reader.take(1)?[0];
            if end > 0x10ffff || classes.last().is_some_and(|range| range.end >= end) {
                return Err(Error::Data("invalid canonical combining class range"));
            }
            classes.push(CombiningClassRange { end, class });
        }
        if classes.last().is_none_or(|range| range.end != 0x10ffff) {
            return Err(Error::Data(
                "combining class ranges must cover U+0000..U+10FFFF",
            ));
        }
        reader.finish()?;
        Ok(Self { mappings, classes })
    }

    pub(crate) fn combining_class(&self, cp: u32) -> u8 {
        self.classes[self.classes.partition_point(|range| range.end < cp)].class
    }

    pub(crate) fn normalize(&self, input: &[u32]) -> Vec<u32> {
        let mut output = Vec::with_capacity(input.len());
        for &cp in input {
            if let Ok(index) = self
                .mappings
                .binary_search_by_key(&cp, |entry| entry.code_point)
            {
                // Exported mappings are already recursively decomposed,
                // including Hangul; ordering across input boundaries follows.
                output.extend_from_slice(&self.mappings[index].decomposition);
            } else {
                output.push(cp);
            }
        }
        let mut nonstarter_start = 0;
        for index in 0..output.len() {
            if self.combining_class(output[index]) == 0 {
                output[nonstarter_start..index].sort_by_key(|cp| self.combining_class(*cp));
                nonstarter_start = index + 1;
            }
        }
        // Stable sorting preserves the order of equal combining classes.
        output[nonstarter_start..].sort_by_key(|cp| self.combining_class(*cp));
        output
    }
}

fn is_scalar(cp: u32) -> bool {
    cp <= 0x10ffff && !(0xd800..=0xdfff).contains(&cp)
}
