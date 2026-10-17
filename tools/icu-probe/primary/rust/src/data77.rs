//! Reads the versioned, development-time ICU 77.1 table export.
//!
//! This contains Unicode collation mappings, not keys for test strings. Context
//! tries are rebuilt from the complete exported UCharsTrie entries. Runtime
//! loading and lookup use only Rust's standard library.

use std::collections::BTreeMap;

use crate::{Error, Result, decode_utf16_units};

#[derive(Debug)]
struct Range<T> {
    end: u32,
    value: T,
}

#[derive(Debug, Default)]
pub(crate) struct ContextNode {
    pub(crate) value: Option<u32>,
    edges: BTreeMap<u32, usize>,
}

#[derive(Debug)]
pub(crate) struct Context {
    pub(crate) default: u32,
    pub(crate) nodes: Vec<ContextNode>,
}

impl Context {
    pub(crate) fn next(&self, node: usize, cp: u32) -> Option<usize> {
        self.nodes[node].edges.get(&cp).copied()
    }

    pub(crate) fn has_next(&self, node: usize) -> bool {
        !self.nodes[node].edges.is_empty()
    }

    fn insert(&mut self, units: &[u16], value: u32) -> Result<()> {
        let cps = decode_utf16_units(units);
        if cps.is_empty() || cps.iter().any(|cp| (0xd800..=0xdfff).contains(cp)) {
            return Err(Error::Data("invalid UTF-16 context entry"));
        }
        let mut node = 0;
        for cp in cps {
            node = if let Some(next) = self.nodes[node].edges.get(&cp) {
                *next
            } else {
                let next = self.nodes.len();
                self.nodes.push(ContextNode::default());
                self.nodes[node].edges.insert(cp, next);
                next
            };
        }
        if self.nodes[node].value.replace(value).is_some() {
            return Err(Error::Data("duplicate context entry"));
        }
        Ok(())
    }
}

/// Immutable, version-checked full root collation data from ICU4C 77.1.
#[derive(Debug)]
pub struct Data77 {
    ranges: Vec<Range<u32>>,
    pub(crate) ce32s: Vec<u32>,
    pub(crate) ces: Vec<u64>,
    pub(crate) jamo: Vec<u32>,
    pub(crate) compressible: [bool; 256],
    fcd: Vec<Range<u16>>,
    contexts: BTreeMap<u32, Context>,
    /// Effective root PRIMARY CollationSettings options, checked on loading.
    pub primary_options: u32,
    /// Exported identity/diagnostic value; root PRIMARY is non-shifted.
    pub variable_top: u32,
    /// Exported identity/diagnostic value; root defaults to numeric OFF.
    pub numeric_primary: u32,
}

impl Data77 {
    /// Decode the documented BRSPRI77 schema and reject incompatible data.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let mut r = Reader { bytes, pos: 0 };
        if r.take(8)? != b"BRSPRI77" || r.u32()? != 1 {
            return Err(Error::Data("unsupported table magic/schema"));
        }
        for expected in [77, 1, 16, 0, 47, 0] {
            if r.u32()? != expected {
                return Err(Error::Data("expected ICU 77.1 / Unicode 16.0 / CLDR 47.0"));
            }
        }
        let primary_options = r.u32()?;
        let variable_top = r.u32()?;
        let numeric_primary = r.u32()?;
        // ICU CollationSettings: CHECK_FCD=1, NUMERIC=2, ALTERNATE_MASK=0xc,
        // CASE_LEVEL=0x400, STRENGTH_MASK=0xf000. Root PRIMARY uses none.
        if primary_options & (0x000f | 0x0400 | 0xf000) != 0 {
            return Err(Error::Data(
                "settings are outside root PRIMARY prototype scope",
            ));
        }

        let count = r.count(8)?;
        let mut ranges = Vec::with_capacity(count);
        for _ in 0..count {
            ranges.push(Range {
                end: r.u32()?,
                value: r.u32()?,
            });
        }
        validate_ranges(&ranges)?;

        let count = r.count(4)?;
        let mut ce32s = Vec::with_capacity(count);
        for _ in 0..count {
            ce32s.push(r.u32()?);
        }
        if ce32s.is_empty() {
            return Err(Error::Data("missing NUL CE32"));
        }

        let count = r.count(8)?;
        let mut ces = Vec::with_capacity(count);
        for _ in 0..count {
            ces.push(r.u64()?);
        }

        let count = r.count(2)?;
        let mut raw_contexts = Vec::with_capacity(count);
        for _ in 0..count {
            raw_contexts.push(r.u16()?);
        }

        let count = r.count(4)?;
        if count != 67 {
            return Err(Error::Data("expected 19+21+27 Jamo CE32s"));
        }
        let mut jamo = Vec::with_capacity(count);
        for _ in 0..count {
            jamo.push(r.u32()?);
        }

        if r.count(1)? != 256 {
            return Err(Error::Data("expected 256 primary compressibility flags"));
        }
        let mut compressible = [false; 256];
        for flag in &mut compressible {
            *flag = match r.take(1)?[0] {
                0 => false,
                1 => true,
                _ => return Err(Error::Data("invalid primary compressibility flag")),
            };
        }

        let count = r.count(6)?;
        let mut fcd = Vec::with_capacity(count);
        for _ in 0..count {
            fcd.push(Range {
                end: r.u32()?,
                value: r.u16()?,
            });
        }
        validate_ranges(&fcd)?;

        let count = r.count(12)?;
        let mut contexts = BTreeMap::new();
        let mut previous_context = None;
        for _ in 0..count {
            let index = r.u32()?;
            let default = r.u32()?;
            if previous_context.is_some_and(|previous| index <= previous) {
                return Err(Error::Data("context indices must be strictly increasing"));
            }
            previous_context = Some(index);
            let raw = raw_contexts
                .get(index as usize..index as usize + 2)
                .ok_or(Error::Data("context default outside raw contexts"))?;
            if default != (u32::from(raw[0]) << 16) | u32::from(raw[1]) {
                return Err(Error::Data("decoded and raw context defaults disagree"));
            }
            let mut context = Context {
                default,
                nodes: vec![ContextNode::default()],
            };
            let entries = r.count(8)?;
            for _ in 0..entries {
                let length = r.count(2)?;
                let mut units = Vec::with_capacity(length);
                for _ in 0..length {
                    units.push(r.u16()?);
                }
                context.insert(&units, r.u32()?)?;
            }
            contexts.insert(index, context);
        }
        if r.pos != bytes.len() {
            return Err(Error::Data("unexpected bytes after final table segment"));
        }
        let data = Self {
            ranges,
            ce32s,
            ces,
            jamo,
            compressible,
            fcd,
            contexts,
            primary_options,
            variable_top,
            numeric_primary,
        };
        data.validate_ce32_references()?;
        Ok(data)
    }

    pub(crate) fn lookup(&self, cp: u32) -> u32 {
        self.ranges[self.ranges.partition_point(|range| range.end < cp)].value
    }

    pub(crate) fn fcd16(&self, cp: u32) -> u16 {
        self.fcd[self.fcd.partition_point(|range| range.end < cp)].value
    }

    pub(crate) fn context(&self, index: u32) -> Result<&Context> {
        self.contexts
            .get(&index)
            .ok_or(Error::Data("missing context index"))
    }

    fn validate_ce32_references(&self) -> Result<()> {
        let values = self
            .ranges
            .iter()
            .map(|range| range.value)
            .chain(self.ce32s.iter().copied())
            .chain(self.jamo.iter().copied())
            .chain(self.contexts.values().flat_map(|context| {
                std::iter::once(context.default)
                    .chain(context.nodes.iter().filter_map(|node| node.value))
            }));
        for ce32 in values {
            if ce32 & 0xff < 0xc0 {
                continue;
            }
            let index = (ce32 >> 13) as usize;
            let length = ((ce32 >> 8) & 31) as usize;
            let valid = match ce32 & 15 {
                1 | 2 | 4 | 11 | 12 | 13 | 15 => true,
                5 => length > 0 && index + length <= self.ce32s.len(),
                6 => length > 0 && index + length <= self.ces.len(),
                8 | 9 => self.contexts.contains_key(&(index as u32)),
                10 => index < self.ce32s.len(),
                14 => index < self.ces.len(),
                // Data tables can include unused builder/sentinel slots. Any
                // such tag reached during iteration is an explicit error.
                _ => true,
            };
            if !valid {
                return Err(Error::Data("CE32 references an invalid table span"));
            }
        }
        Ok(())
    }
}

fn validate_ranges<T>(ranges: &[Range<T>]) -> Result<()> {
    if ranges.is_empty()
        || ranges.last().is_none_or(|range| range.end != 0x10ffff)
        || ranges.windows(2).any(|pair| pair[0].end >= pair[1].end)
    {
        return Err(Error::Data("ranges must partition U+0000..U+10FFFF"));
    }
    Ok(())
}

struct Reader<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn take(&mut self, length: usize) -> Result<&'a [u8]> {
        let end = self
            .pos
            .checked_add(length)
            .ok_or(Error::Data("table length overflow"))?;
        let value = self
            .bytes
            .get(self.pos..end)
            .ok_or(Error::Data("truncated table"))?;
        self.pos = end;
        Ok(value)
    }

    fn u16(&mut self) -> Result<u16> {
        Ok(u16::from_le_bytes(
            self.take(2)?.try_into().expect("checked length"),
        ))
    }

    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(
            self.take(4)?.try_into().expect("checked length"),
        ))
    }

    fn u64(&mut self) -> Result<u64> {
        Ok(u64::from_le_bytes(
            self.take(8)?.try_into().expect("checked length"),
        ))
    }

    fn count(&mut self, minimum_width: usize) -> Result<usize> {
        let count = self.u32()? as usize;
        if count > (self.bytes.len() - self.pos) / minimum_width {
            return Err(Error::Data("table count exceeds remaining data"));
        }
        Ok(count)
    }
}
