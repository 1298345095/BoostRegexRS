// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2010-2014, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 FCDUTF16CollationIterator and collationfcd.h.
// See ../NOTICE.md, ../LOCALE-MECHANISMS.md and ../../data/LICENSE-ICU.txt.

//! Bidirectional character cursor with optional incremental FCD checking.

use crate::{Data77, Error, NfdData77, Result};

/// Indices are code-point cursor positions, never public regex input offsets.
/// Raw input stays intact; only a failing local segment acquires an NFD buffer.
pub(crate) struct Cursor<'a> {
    raw: &'a [u32],
    data: &'a Data77,
    nfd: Option<&'a NfdData77>,
    pos: usize,
    start: usize,
    limit: usize,
    segment_start: usize,
    segment_limit: usize,
    check_dir: i8,
    normalized: Vec<u32>,
    in_normalized: bool,
}

impl<'a> Cursor<'a> {
    pub(crate) fn new(data: &'a Data77, raw: &'a [u32], nfd: Option<&'a NfdData77>) -> Self {
        Self {
            raw,
            data,
            nfd,
            pos: 0,
            start: 0,
            limit: raw.len(),
            segment_start: 0,
            segment_limit: 0,
            check_dir: 1,
            normalized: Vec::new(),
            in_normalized: false,
        }
    }

    pub(crate) fn position_cp(&self) -> usize {
        if !self.in_normalized {
            self.pos
        } else if self.pos == self.start {
            self.segment_start
        } else {
            self.segment_limit
        }
    }

    pub(crate) fn next(&mut self) -> Option<u32> {
        if self.nfd.is_none() {
            let cp = self.raw.get(self.pos).copied()?;
            self.pos += 1;
            return Some(cp);
        }
        loop {
            if self.check_dir > 0 {
                if self.pos == self.limit {
                    return None;
                }
                let cp = self.raw[self.pos];
                let unit = first_unit(cp);
                let next_unit = if cp > 0xffff {
                    Some(last_unit(cp))
                } else {
                    self.raw.get(self.pos + 1).copied().map(first_unit)
                };
                if self.data.fcd_has_tccc(unit)
                    && (maybe_tibetan_composite(unit)
                        || next_unit.is_some_and(|next| self.data.fcd_has_lccc(next)))
                {
                    self.next_segment();
                }
                return Some(self.take_next());
            } else if self.check_dir == 0 && self.pos != self.limit {
                return Some(self.take_next());
            } else {
                self.switch_forward();
            }
        }
    }

    pub(crate) fn previous(&mut self) -> Option<u32> {
        if self.nfd.is_none() {
            self.pos = self.pos.checked_sub(1)?;
            return Some(self.raw[self.pos]);
        }
        loop {
            if self.check_dir < 0 {
                if self.pos == self.start {
                    return None;
                }
                let cp = self.raw[self.pos - 1];
                let unit = last_unit(cp);
                let previous_unit = if cp > 0xffff {
                    Some(first_unit(cp))
                } else {
                    self.pos
                        .checked_sub(2)
                        .map(|index| last_unit(self.raw[index]))
                };
                if self.data.fcd_has_lccc(unit)
                    && (maybe_tibetan_composite(unit)
                        || previous_unit.is_some_and(|previous| self.data.fcd_has_tccc(previous)))
                {
                    self.previous_segment();
                }
                return Some(self.take_previous());
            } else if self.check_dir == 0 && self.pos != self.start {
                return Some(self.take_previous());
            } else {
                self.switch_backward();
            }
        }
    }

    pub(crate) fn backward(&mut self, count: usize) -> Result<()> {
        for _ in 0..count {
            self.previous()
                .ok_or(Error::Data("input cursor underflow"))?;
        }
        Ok(())
    }

    pub(crate) fn forward(&mut self, count: usize) -> Result<()> {
        for _ in 0..count {
            self.next().ok_or(Error::Data("input cursor overflow"))?;
        }
        Ok(())
    }

    fn take_next(&mut self) -> u32 {
        let cp = if self.in_normalized {
            self.normalized[self.pos]
        } else {
            self.raw[self.pos]
        };
        self.pos += 1;
        cp
    }

    fn take_previous(&mut self) -> u32 {
        self.pos -= 1;
        if self.in_normalized {
            self.normalized[self.pos]
        } else {
            self.raw[self.pos]
        }
    }

    fn switch_forward(&mut self) {
        if self.check_dir < 0 {
            self.start = self.pos;
            self.segment_start = self.pos;
            if self.pos == self.segment_limit {
                self.limit = self.raw.len();
                self.check_dir = 1;
            } else {
                self.check_dir = 0;
            }
        } else {
            if self.in_normalized {
                self.pos = self.segment_limit;
                self.start = self.segment_limit;
                self.segment_start = self.segment_limit;
                self.in_normalized = false;
            }
            self.limit = self.raw.len();
            self.check_dir = 1;
        }
    }

    fn next_segment(&mut self) {
        let from = self.pos;
        let mut p = from;
        let mut previous_cc = 0;
        loop {
            let q = p;
            let fcd = self.data.fcd16(self.raw[p]);
            p += 1;
            let lead_cc = fcd >> 8;
            if lead_cc == 0 && q != from {
                self.limit = q;
                self.segment_limit = q;
                break;
            }
            if lead_cc != 0 && (previous_cc > lead_cc || is_tibetan_composite(fcd)) {
                while p < self.raw.len() && self.data.fcd16(self.raw[p]) > 0xff {
                    p += 1;
                }
                self.normalize(from, p);
                self.pos = self.start;
                break;
            }
            previous_cc = fcd & 0xff;
            if p == self.raw.len() || previous_cc == 0 {
                self.limit = p;
                self.segment_limit = p;
                break;
            }
        }
        self.check_dir = 0;
    }

    fn switch_backward(&mut self) {
        if self.check_dir > 0 {
            self.limit = self.pos;
            self.segment_limit = self.pos;
            if self.pos == self.segment_start {
                self.start = 0;
                self.check_dir = -1;
            } else {
                self.check_dir = 0;
            }
        } else {
            if self.in_normalized {
                self.pos = self.segment_start;
                self.limit = self.segment_start;
                self.segment_limit = self.segment_start;
                self.in_normalized = false;
            }
            self.start = 0;
            self.check_dir = -1;
        }
    }

    fn previous_segment(&mut self) {
        let to = self.pos;
        let mut p = to;
        let mut next_cc = 0;
        loop {
            let q = p;
            p -= 1;
            let mut fcd = self.data.fcd16(self.raw[p]);
            let trail_cc = fcd & 0xff;
            if trail_cc == 0 && q != to {
                self.start = q;
                self.segment_start = q;
                break;
            }
            if trail_cc != 0 && ((next_cc != 0 && trail_cc > next_cc) || is_tibetan_composite(fcd))
            {
                let mut from;
                loop {
                    from = p;
                    if fcd <= 0xff || p == 0 {
                        break;
                    }
                    p -= 1;
                    fcd = self.data.fcd16(self.raw[p]);
                    if fcd == 0 {
                        break;
                    }
                }
                self.normalize(from, to);
                self.pos = self.limit;
                break;
            }
            next_cc = fcd >> 8;
            if p == 0 || next_cc == 0 {
                self.start = p;
                self.segment_start = p;
                break;
            }
        }
        self.check_dir = 0;
    }

    fn normalize(&mut self, from: usize, to: usize) {
        self.normalized = self
            .nfd
            .expect("FCD checking enabled")
            .normalize(&self.raw[from..to]);
        self.segment_start = from;
        self.segment_limit = to;
        self.start = 0;
        self.limit = self.normalized.len();
        self.in_normalized = true;
    }
}

fn is_tibetan_composite(fcd: u16) -> bool {
    fcd == 0x8182 || fcd == 0x8184
}

// The fast checks must observe the original UTF-16 units even though segment
// storage uses full code points. Replacing a previous trail surrogate by its
// supplementary scalar's Tccc changes ICU77's backward segment boundaries.
pub(crate) fn first_unit(cp: u32) -> u16 {
    if cp <= 0xffff {
        cp as u16
    } else {
        ((cp >> 10) + 0xd7c0) as u16
    }
}

fn last_unit(cp: u32) -> u16 {
    if cp <= 0xffff {
        cp as u16
    } else {
        ((cp & 0x3ff) | 0xdc00) as u16
    }
}

fn maybe_tibetan_composite(unit: u16) -> bool {
    unit & 0xff01 == 0x0f01
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn frozen_native_three_direction_traces_match_original_utf16_offsets() {
        let data = Data77::from_bytes(include_bytes!("../../data/root-icu77.bin")).unwrap();
        let nfd = NfdData77::from_bytes(include_bytes!("../../data/root-icu77-nfd.bin")).unwrap();
        let inputs = include_str!("../tests/data/fcd77/inputs-u16.tsv");
        let mut expected = include_str!("../tests/data/fcd77/native-cursor.tsv").lines();
        assert_eq!(
            expected.next(),
            Some("case_id\tdirection\tindex\tcode_point_hex\tutf16_offset_after\tterminal")
        );
        let mut cases = 0;
        for line in inputs.lines().skip(1) {
            let (id, encoded) = line.split_once('\t').unwrap();
            let units = encoded
                .split(',')
                .filter(|field| !field.is_empty())
                .map(|field| u16::from_str_radix(field, 16).unwrap());
            let raw = char::decode_utf16(units)
                .map(|value| u32::from(value.unwrap()))
                .collect::<Vec<_>>();
            let mut offsets = vec![0];
            for &cp in &raw {
                offsets.push(offsets.last().unwrap() + if cp > 0xffff { 2 } else { 1 });
            }
            let mut cursor = Cursor::new(&data, &raw, Some(&nfd));
            for direction in ["forward-1", "backward", "forward-2"] {
                for index in 0.. {
                    let cp = if direction == "backward" {
                        cursor.previous()
                    } else {
                        cursor.next()
                    };
                    let row = expected.next().expect("missing native cursor row");
                    let fields = row.split('\t').collect::<Vec<_>>();
                    assert_eq!(fields.len(), 6, "{row}");
                    assert_eq!(fields[0], id, "{row}");
                    assert_eq!(fields[1], direction, "{row}");
                    assert_eq!(fields[2].parse::<usize>().unwrap(), index, "{row}");
                    let native_cp = (!fields[3].is_empty())
                        .then(|| u32::from_str_radix(fields[3], 16).unwrap());
                    assert_eq!(cp, native_cp, "{row}");
                    assert_eq!(
                        offsets[cursor.position_cp()],
                        fields[4].parse::<usize>().unwrap(),
                        "{row}"
                    );
                    assert_eq!(fields[5] == "1", cp.is_none(), "{row}");
                    if cp.is_none() {
                        break;
                    }
                }
            }
            cases += 1;
        }
        assert!(
            cases >= 6,
            "both full failures and their four reductions are required"
        );
        assert!(expected.next().is_none(), "uncompared native cursor rows");
    }
}
