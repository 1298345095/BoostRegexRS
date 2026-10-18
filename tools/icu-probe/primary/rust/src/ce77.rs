// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2010-2014, International Business Machines Corporation and others.
// Copyright (C) 2010-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU 77.1 collationiterator.cpp, collation.h, collation.cpp.
// See ../NOTICE.md and ../../data/LICENSE-ICU.txt for provenance and license.

//! Forward ICU77 CE iteration, with owner-aware data and an optional FCD cursor.
//!
//! The representation differs from ICU: decoded code points replace its UTF-16
//! cursor and decoded context node IDs replace UCharsTrie byte offsets. Skipped
//! combining marks retain their separate cursor and are emitted after a matched
//! discontiguous contraction, including nested matching against remaining input.

use crate::cursor77::{Cursor, first_unit};
use crate::data77::{Context, Data77};
use crate::{Error, NfdData77, Result, TraceEvent};

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
    input: Cursor<'a>,
    numeric: bool,
    skipped: Skipped,
    ces: Vec<u64>,
    trace: Option<Vec<TraceEvent>>,
}

impl<'a> Elements<'a> {
    pub(crate) fn new(data: &'a Data77, input: &'a [u32], trace: bool) -> Self {
        Self::with_options(data, input, None, false, trace)
    }

    pub(crate) fn with_options(
        data: &'a Data77,
        input: &'a [u32],
        nfd: Option<&'a NfdData77>,
        numeric: bool,
        trace: bool,
    ) -> Self {
        Self {
            data,
            input: Cursor::new(data, input, nfd),
            numeric,
            skipped: Skipped::default(),
            ces: Vec::new(),
            trace: trace.then(Vec::new),
        }
    }

    pub(crate) fn collect(mut self) -> Result<(Vec<u64>, Option<Vec<TraceEvent>>)> {
        while let Some(cp) = self.next_normal() {
            let (data, ce32) = self.data.resolve(cp)?;
            self.append(data, Some(cp), ce32)?;
        }
        self.emit(None, 1, NO_CE, "end");
        Ok((self.ces, self.trace))
    }

    fn next_normal(&mut self) -> Option<u32> {
        self.input.next()
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
        self.input.backward(normal_count)
    }

    fn event(&mut self, cp: Option<u32>, ce32: u32, kind: &'static str, ce: Option<u64>) {
        if let Some(trace) = &mut self.trace {
            trace.push(TraceEvent {
                input_position_cp: self.input.position_cp(),
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

    fn append(&mut self, data: &'a Data77, cp: Option<u32>, mut ce32: u32) -> Result<()> {
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
                    ce32 = self.prefix(data, ce32)?;
                }
                9 => {
                    self.event(cp, ce32, "contraction", None);
                    let context = data.context(index as u32)?;
                    let Some(next_cp) = self.next_skipped() else {
                        ce32 = context.default;
                        continue;
                    };
                    if ce32 & 0x200 != 0 && !data.fcd_has_lccc(first_unit(next_cp)) {
                        self.backward_skipped(1)?;
                        ce32 = context.default;
                        continue;
                    }
                    match self.contraction(data, context, ce32, next_cp)? {
                        ContractionResult::Ce32(value) => ce32 = value,
                        ContractionResult::Appended => return Ok(()),
                    }
                }
                10 => {
                    if self.numeric {
                        self.append_numeric(ce32)?;
                        return Ok(());
                    }
                    self.event(cp, ce32, "digit_numeric_off", None);
                    ce32 = *data
                        .ce32s
                        .get(index)
                        .ok_or(Error::Data("digit outside CE32 table"))?;
                }
                11 => {
                    self.event(cp, ce32, "embedded_nul", None);
                    // Explicit-length input: NUL never terminates iteration.
                    ce32 = *data.ce32s.first().ok_or(Error::Data("missing NUL CE32"))?;
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
                    self.append(data, None, data.jamo[l])?;
                    self.append(data, None, data.jamo[19 + v])?;
                    if t != 0 {
                        self.append(data, None, data.jamo[39 + t])?;
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
                    let value = *data
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

    fn prefix(&mut self, data: &'a Data77, ce32: u32) -> Result<u32> {
        let context = data.context(ce32 >> 13)?;
        let mut result = context.default;
        let mut node = 0;
        // ICU backs over the current code point in the real input, looks behind
        // through prefixes, then restores its cursor. The selected plain/FCD
        // cursor handles those steps, never the transient skipped-marks buffer.
        self.input.backward(1)?;
        let mut lookbehind = 0;
        while let Some(cp) = self.input.previous() {
            lookbehind += 1;
            let Some(next) = context.next(node, cp) else {
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
        self.input.forward(lookbehind + 1)?;
        Ok(result)
    }

    fn contraction(
        &mut self,
        data: &'a Data77,
        context: &Context,
        original: u32,
        mut cp: u32,
    ) -> Result<ContractionResult> {
        let mut node = context.next(0, cp);
        let mut last_match_node = 0;
        let mut result = context.default;
        let mut since_match = 1;
        let mut look_ahead = 1;
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
                            look_ahead -= since_match - 1;
                            since_match = 1;
                        }
                        if self.data.fcd16(cp) > 0xff {
                            return self.discontiguous(
                                data,
                                context,
                                last_match_node,
                                result,
                                look_ahead,
                                cp,
                            );
                        }
                    }
                    self.backward_skipped(since_match)?;
                    return Ok(ContractionResult::Ce32(result));
                }
            }
            look_ahead += 1;
            node = node.and_then(|n| context.next(n, cp));
        }
    }

    fn discontiguous(
        &mut self,
        data: &'a Data77,
        context: &Context,
        node: usize,
        mut result: u32,
        mut look_ahead: usize,
        first_skipped: u32,
    ) -> Result<ContractionResult> {
        let mut previous_cc = self.data.fcd16(first_skipped) & 0xff;
        let Some(mut cp) = self.next_skipped() else {
            self.backward_skipped(1)?;
            return Ok(ContractionResult::Ce32(result));
        };
        look_ahead += 1;
        let mut fcd16 = self.data.fcd16(cp);
        if fcd16 <= 0xff {
            self.backward_skipped(2)?;
            return Ok(ContractionResult::Ce32(result));
        }
        let mut node = Some(node);
        if self.skipped.old.is_empty() {
            node = Some(0);
            if look_ahead > 2 {
                // ICU replays the matched suffix through the real cursor.
                // This is observable with incremental FCD: turning around can
                // select a different local segment, so cached trie state alone
                // cannot replace the backward/forward character operations.
                self.input.backward(look_ahead)?;
                let replay = self
                    .input
                    .next()
                    .ok_or(Error::Data("missing contraction replay character"))?;
                node = context.next(0, replay);
                for _ in 3..look_ahead {
                    let replay = self
                        .input
                        .next()
                        .ok_or(Error::Data("missing contraction replay character"))?;
                    node = node.and_then(|current| context.next(current, replay));
                }
                self.input.forward(2)?;
            }
        }
        self.event(Some(first_skipped), result, "discontiguous_start", None);
        self.skipped.first_skipped(first_skipped);
        let mut saved_node = node;
        let mut since_match = 2;
        loop {
            let matched = if previous_cc < fcd16 >> 8 {
                node.and_then(|current| context.next(current, cp))
                    .and_then(|next| context.nodes[next].value.map(|value| (next, value)))
            } else {
                None
            };
            if let Some((next, value)) = matched {
                node = Some(next);
                result = value;
                since_match = 0;
                self.skipped.matched_length = self.skipped.new.len();
                self.event(Some(cp), result, "discontiguous_match", None);
                if !context.has_next(next) {
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
            self.append(data, None, result)?;
            while self.skipped.has_next() {
                let cp = self.skipped.next().expect("has_next");
                let (owner, ce32) = self.data.resolve(cp)?;
                self.append(owner, Some(cp), ce32)?;
            }
            self.skipped.clear();
            Ok(ContractionResult::Appended)
        } else {
            Ok(ContractionResult::Ce32(result))
        }
    }

    fn append_numeric(&mut self, first_ce32: u32) -> Result<()> {
        let mut digits = vec![((first_ce32 >> 8) & 15) as u8];
        while let Some(cp) = self.next_normal() {
            let (_, ce32) = self.data.resolve(cp)?;
            if ce32 & 0xff < SPECIAL || ce32 & 15 != 10 {
                // ICU's numeric scanner uses the real cursor, independently of
                // discontiguous contraction skipped-mark bookkeeping.
                self.input.backward(1)?;
                break;
            }
            digits.push(((ce32 >> 8) & 15) as u8);
        }
        for ce in crate::numeric77::numeric_ces(&digits, self.data.numeric_primary) {
            self.emit(None, first_ce32, ce, "numeric");
        }
        Ok(())
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
