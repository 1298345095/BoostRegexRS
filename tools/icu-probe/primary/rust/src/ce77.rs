// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2010-2014, International Business Machines Corporation and others.
// Copyright (C) 2010-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU 77.1 collationiterator.cpp, collation.h, collation.cpp.
// See ../NOTICE.md and ../../data/LICENSE-ICU.txt for provenance and license.

//! Ordinary forward ICU77 CE iteration, with normalization deliberately OFF.
//!
//! The representation differs from ICU: decoded code points replace its UTF-16
//! cursor and decoded context node IDs replace UCharsTrie byte offsets. Skipped
//! combining marks retain their separate cursor and are emitted after a matched
//! discontiguous contraction, including nested matching against remaining input.

use crate::data77::{Context, Data77};
use crate::{Error, Result, TraceEvent};

const SPECIAL: u32 = 0xc0;
pub(crate) const NO_CE: u64 = 0x0000_0001_0100_0100;
const COMMON_SEC_TER: u64 = 0x0500_0500;

#[derive(Default)]
struct Skipped {
    old: Vec<u32>,
    new: Vec<u32>,
    pos: usize,
    matched_length: usize,
}

impl Skipped {
    fn has_next(&self) -> bool {
        self.pos < self.old.len()
    }

    fn next(&mut self) -> Option<u32> {
        let cp = self.old.get(self.pos).copied()?;
        self.pos += 1;
        Some(cp)
    }

    fn first_skipped(&mut self, cp: u32) {
        self.new.clear();
        self.new.push(cp);
        self.matched_length = 0;
    }

    fn replace_match(&mut self) {
        self.old.splice(
            ..self.pos.min(self.old.len()),
            self.new[..self.matched_length].iter().copied(),
        );
        self.pos = 0;
    }

    fn clear(&mut self) {
        self.old.clear();
        self.pos = 0;
    }
}

enum ContractionResult {
    Ce32(u32),
    Appended,
}

pub(crate) struct Elements<'a> {
    data: &'a Data77,
    input: &'a [u32],
    pos: usize,
    skipped: Skipped,
    ces: Vec<u64>,
    trace: Option<Vec<TraceEvent>>,
}

impl<'a> Elements<'a> {
    pub(crate) fn new(data: &'a Data77, input: &'a [u32], trace: bool) -> Self {
        Self {
            data,
            input,
            pos: 0,
            skipped: Skipped::default(),
            ces: Vec::new(),
            trace: trace.then(Vec::new),
        }
    }

    pub(crate) fn collect(mut self) -> Result<(Vec<u64>, Option<Vec<TraceEvent>>)> {
        while let Some(cp) = self.next_normal() {
            self.append(Some(cp), self.data.lookup(cp))?;
        }
        self.emit(None, 1, NO_CE, "end");
        Ok((self.ces, self.trace))
    }

    fn next_normal(&mut self) -> Option<u32> {
        let cp = self.input.get(self.pos).copied()?;
        self.pos += 1;
        Some(cp)
    }

    fn next_skipped(&mut self) -> Option<u32> {
        if let Some(cp) = self.skipped.next() {
            return Some(cp);
        }
        let cp = self.next_normal()?;
        if !self.skipped.old.is_empty() {
            // Position beyond old.len() counts code points read from real input.
            self.skipped.pos += 1;
        }
        Some(cp)
    }

    fn backward_skipped(&mut self, count: usize) -> Result<()> {
        let normal_count = if self.skipped.old.is_empty() {
            count
        } else {
            let beyond = self.skipped.pos.saturating_sub(self.skipped.old.len());
            self.skipped.pos = self
                .skipped
                .pos
                .checked_sub(count)
                .ok_or(Error::Data("skipped cursor underflow"))?;
            beyond.min(count)
        };
        self.pos = self
            .pos
            .checked_sub(normal_count)
            .ok_or(Error::Data("input cursor underflow"))?;
        Ok(())
    }

    fn event(&mut self, cp: Option<u32>, ce32: u32, kind: &'static str, ce: Option<u64>) {
        if let Some(trace) = &mut self.trace {
            trace.push(TraceEvent {
                input_position_cp: self.pos,
                code_point: cp,
                ce32,
                kind,
                ce,
            });
        }
    }

    fn emit(&mut self, cp: Option<u32>, ce32: u32, ce: u64, kind: &'static str) {
        self.ces.push(ce);
        self.event(cp, ce32, kind, Some(ce));
    }

    fn append(&mut self, cp: Option<u32>, mut ce32: u32) -> Result<()> {
        while ce32 & 0xff >= SPECIAL {
            let index = (ce32 >> 13) as usize;
            let length = ((ce32 >> 8) & 31) as usize;
            match ce32 & 15 {
                0 | 3 | 7 => return Err(Error::UnsupportedCe32(ce32)),
                1 => {
                    self.emit(cp, ce32, long_primary_ce(ce32), "long_primary");
                    return Ok(());
                }
                2 => {
                    self.emit(cp, ce32, u64::from(ce32 & 0xffffff00), "long_secondary");
                    return Ok(());
                }
                4 => {
                    let first = (u64::from(ce32 & 0xff000000) << 32)
                        | 0x05000000
                        | u64::from((ce32 & 0xff0000) >> 8);
                    let second = u64::from((ce32 & 0xff00) << 16) | 0x0500;
                    self.emit(cp, ce32, first, "latin_expansion_0");
                    self.emit(cp, ce32, second, "latin_expansion_1");
                    return Ok(());
                }
                5 => {
                    let data = self.data;
                    let values = data
                        .ce32s
                        .get(index..index + length)
                        .ok_or(Error::Data("expansion32 outside table"))?;
                    for value in values {
                        self.emit(cp, *value, simple_or_long_ce(*value)?, "expansion32");
                    }
                    return Ok(());
                }
                6 => {
                    let data = self.data;
                    let values = data
                        .ces
                        .get(index..index + length)
                        .ok_or(Error::Data("expansion64 outside table"))?;
                    for value in values {
                        self.emit(cp, ce32, *value, "expansion64");
                    }
                    return Ok(());
                }
                8 => {
                    self.event(cp, ce32, "prefix", None);
                    ce32 = self.prefix(ce32)?;
                }
                9 => {
                    self.event(cp, ce32, "contraction", None);
                    let data = self.data;
                    let context = data.context(index as u32)?;
                    let Some(next_cp) = self.next_skipped() else {
                        ce32 = context.default;
                        continue;
                    };
                    // ICU uses a fast mayHaveLccc test. Exact FCD16 has the
                    // same rejection condition without the conservative filter.
                    if ce32 & 0x200 != 0 && data.fcd16(next_cp) <= 0xff {
                        self.backward_skipped(1)?;
                        ce32 = context.default;
                        continue;
                    }
                    match self.contraction(context, ce32, next_cp)? {
                        ContractionResult::Ce32(value) => ce32 = value,
                        ContractionResult::Appended => return Ok(()),
                    }
                }
                10 => {
                    self.event(cp, ce32, "digit_numeric_off", None);
                    ce32 = *self
                        .data
                        .ce32s
                        .get(index)
                        .ok_or(Error::Data("digit outside CE32 table"))?;
                }
                11 => {
                    self.event(cp, ce32, "embedded_nul", None);
                    // Explicit-length input: NUL never terminates iteration.
                    ce32 = self.data.ce32s[0];
                }
                12 => {
                    self.event(cp, ce32, "hangul", None);
                    let syllable = cp
                        .filter(|c| (0xac00..=0xd7a3).contains(c))
                        .ok_or(Error::Data("Hangul tag on non-syllable"))?
                        - 0xac00;
                    let t = (syllable % 28) as usize;
                    let v = ((syllable / 28) % 21) as usize;
                    let l = (syllable / (28 * 21)) as usize;
                    self.append(None, self.data.jamo[l])?;
                    self.append(None, self.data.jamo[19 + v])?;
                    if t != 0 {
                        self.append(None, self.data.jamo[39 + t])?;
                    }
                    return Ok(());
                }
                13 => {
                    // The code-point cursor already combined every valid pair.
                    // Only the explicitly named raw ICU UTF-16 diagnostic can
                    // reach an unpaired lead; ICU gives it implicit weight.
                    if cp.is_none_or(|c| !(0xd800..=0xdbff).contains(&c)) {
                        return Err(Error::Data("lead-surrogate tag on non-lead"));
                    }
                    ce32 = 0xffffffff;
                }
                14 => {
                    let c = cp.ok_or(Error::Data("offset requires a code point"))?;
                    let value = *self
                        .data
                        .ces
                        .get(index)
                        .ok_or(Error::Data("offset outside CE table"))?;
                    self.emit(cp, ce32, make_ce(offset_primary(c, value)?), "offset");
                    return Ok(());
                }
                15 => {
                    let c = cp.ok_or(Error::Data("implicit requires a code point"))?;
                    self.emit(cp, ce32, make_ce(implicit_primary(c)), "implicit");
                    return Ok(());
                }
                _ => unreachable!("four-bit tag"),
            }
        }
        self.emit(cp, ce32, simple_ce(ce32), "simple");
        Ok(())
    }

    fn prefix(&self, ce32: u32) -> Result<u32> {
        let context = self.data.context(ce32 >> 13)?;
        let mut result = context.default;
        let mut node = 0;
        // ICU backs over the current code point in the real input, looks behind
        // through prefixes, then restores its cursor. It does not normalize or
        // match a prefix against the transient skipped-marks buffer.
        let start = self
            .pos
            .checked_sub(1)
            .ok_or(Error::Data("prefix cursor underflow"))?;
        for cp in self.input[..start].iter().rev() {
            let Some(next) = context.next(node, *cp) else {
                break;
            };
            node = next;
            if let Some(value) = context.nodes[node].value {
                result = value;
            }
            if !context.has_next(node) {
                break;
            }
        }
        Ok(result)
    }

    fn contraction(
        &mut self,
        context: &Context,
        original: u32,
        mut cp: u32,
    ) -> Result<ContractionResult> {
        let mut node = context.next(0, cp);
        let mut last_match_node = 0;
        let mut result = context.default;
        let mut since_match = 1;
        let mut matched_suffix = false;
        loop {
            if let Some(value) = node.and_then(|n| context.nodes[n].value) {
                let matched_node = node.expect("value has a node");
                result = value;
                last_match_node = matched_node;
                matched_suffix = true;
                if !context.has_next(matched_node) {
                    return Ok(ContractionResult::Ce32(result));
                }
                let Some(next_cp) = self.next_skipped() else {
                    return Ok(ContractionResult::Ce32(result));
                };
                cp = next_cp;
                since_match = 1;
            } else {
                // A partial match without a value is not "a match in the
                // table". Discontiguous matching resumes at the last value.
                let next_cp = node.and_then(|_| self.next_skipped());
                if let Some(next_cp) = next_cp {
                    cp = next_cp;
                    since_match += 1;
                } else {
                    let trailing_ccc = original & 0x400 != 0;
                    let can_extend_single = original & 0x100 == 0;
                    if trailing_ccc && (can_extend_single || matched_suffix) {
                        if since_match > 1 {
                            self.backward_skipped(since_match)?;
                            cp = self
                                .next_skipped()
                                .ok_or(Error::Data("missing replay character"))?;
                            since_match = 1;
                        }
                        if self.data.fcd16(cp) > 0xff {
                            // Retaining a decoded node ID replaces ICU's saved
                            // UCharsTrie state/replay, with the same last match.
                            return self.discontiguous(context, last_match_node, result, cp);
                        }
                    }
                    self.backward_skipped(since_match)?;
                    return Ok(ContractionResult::Ce32(result));
                }
            }
            node = node.and_then(|n| context.next(n, cp));
        }
    }

    fn discontiguous(
        &mut self,
        context: &Context,
        mut node: usize,
        mut result: u32,
        first_skipped: u32,
    ) -> Result<ContractionResult> {
        let mut previous_cc = self.data.fcd16(first_skipped) & 0xff;
        let Some(mut cp) = self.next_skipped() else {
            self.backward_skipped(1)?;
            return Ok(ContractionResult::Ce32(result));
        };
        let mut fcd16 = self.data.fcd16(cp);
        if fcd16 <= 0xff {
            self.backward_skipped(2)?;
            return Ok(ContractionResult::Ce32(result));
        }
        self.event(Some(first_skipped), result, "discontiguous_start", None);
        self.skipped.first_skipped(first_skipped);
        let mut saved_node = node;
        let mut since_match = 2;
        loop {
            let matched = if previous_cc < fcd16 >> 8 {
                context
                    .next(node, cp)
                    .and_then(|next| context.nodes[next].value.map(|value| (next, value)))
            } else {
                None
            };
            if let Some((next, value)) = matched {
                node = next;
                result = value;
                since_match = 0;
                self.skipped.matched_length = self.skipped.new.len();
                self.event(Some(cp), result, "discontiguous_match", None);
                if !context.has_next(node) {
                    break;
                }
                saved_node = node;
                // The previous skipped character still blocks equal/lower CCC.
            } else {
                self.skipped.new.push(cp);
                node = saved_node;
                previous_cc = fcd16 & 0xff;
            }
            let Some(next_cp) = self.next_skipped() else {
                break;
            };
            cp = next_cp;
            since_match += 1;
            fcd16 = self.data.fcd16(cp);
            if fcd16 <= 0xff {
                break;
            }
        }
        self.backward_skipped(since_match)?;
        let top = self.skipped.old.is_empty();
        self.skipped.replace_match();
        if top && !self.skipped.old.is_empty() {
            self.append(None, result)?;
            while self.skipped.has_next() {
                let cp = self.skipped.next().expect("has_next");
                self.append(Some(cp), self.data.lookup(cp))?;
            }
            self.skipped.clear();
            Ok(ContractionResult::Appended)
        } else {
            Ok(ContractionResult::Ce32(result))
        }
    }
}

fn simple_ce(ce32: u32) -> u64 {
    (u64::from(ce32 & 0xffff0000) << 32)
        | u64::from((ce32 & 0xff00) << 16)
        | u64::from((ce32 & 0xff) << 8)
}

fn long_primary_ce(ce32: u32) -> u64 {
    make_ce(ce32 & 0xffffff00)
}

fn simple_or_long_ce(ce32: u32) -> Result<u64> {
    if ce32 & 0xff < SPECIAL {
        Ok(simple_ce(ce32))
    } else {
        match ce32 & 15 {
            1 => Ok(long_primary_ce(ce32)),
            2 => Ok(u64::from(ce32 & 0xffffff00)),
            _ => Err(Error::Data("expansion32 member is not simple/long")),
        }
    }
}

fn make_ce(primary: u32) -> u64 {
    (u64::from(primary) << 32) | COMMON_SEC_TER
}

fn offset_primary(cp: u32, data_ce: u64) -> Result<u32> {
    let base = (data_ce >> 32) as u32;
    let lower = data_ce as u32;
    let delta = cp
        .checked_sub(lower >> 8)
        .ok_or(Error::Data("negative primary offset"))?;
    let mut offset = delta * (lower & 0x7f);
    offset += ((base >> 8) & 0xff)
        .checked_sub(2)
        .ok_or(Error::Data("invalid offset third byte"))?;
    let mut primary = (offset % 254 + 2) << 8;
    offset /= 254;
    let (minimum, count) = if lower & 0x80 != 0 {
        (4, 251)
    } else {
        (2, 254)
    };
    offset += ((base >> 16) & 0xff)
        .checked_sub(minimum)
        .ok_or(Error::Data("invalid offset second byte"))?;
    primary |= (offset % count + minimum) << 16;
    offset /= count;
    Ok(primary | ((base & 0xff000000) + (offset << 24)))
}

fn implicit_primary(cp: u32) -> u32 {
    let mut c = cp + 1;
    let mut primary = 2 + (c % 18) * 14;
    c /= 18;
    primary |= (2 + c % 254) << 8;
    c /= 254;
    primary | ((4 + c % 251) << 16) | 0xfe000000
}
