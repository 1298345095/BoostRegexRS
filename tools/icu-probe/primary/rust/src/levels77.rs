// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2012-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 collationkeys.{h,cpp}, all published settings.
// See ../NOTICE.md, ../LOCALE-MECHANISMS.md and ../../data/LICENSE-ICU.txt.

//! Complete ICU77 key-level encoding for effective collation settings.

use crate::ce77::NO_CE;
use crate::settings77::{ALTERNATE_MASK, BACKWARD_SECONDARY, CASE_LEVEL, UPPER_FIRST};
use crate::{Settings77, Strength};

const MERGE_PRIMARY: u32 = 0x0200_0000;
const COMMON: u32 = 0x0500;
const NO_CE_WEIGHT: u32 = 0x0100;

pub(crate) fn sort_key(
    ces: &[u64],
    compressible: &[bool; 256],
    settings: &Settings77,
    identical_nfd: &[u32],
) -> Vec<u8> {
    let strength = settings.strength();
    let secondary_enabled = strength != Strength::Primary;
    let case_enabled = settings.options & CASE_LEVEL != 0;
    let tertiary_enabled = !matches!(strength, Strength::Primary | Strength::Secondary);
    let quaternary_enabled = matches!(strength, Strength::Quaternary | Strength::Identical);
    let shifted = settings.options & ALTERNATE_MASK != 0;
    let variable_limit = if shifted {
        settings.variable_top + 1
    } else {
        0
    };
    let mut result = Vec::new();
    let mut previous_primary = 0;
    let mut secondary = SecondaryLevel::default();
    let mut cases = CaseLevel::default();
    let mut tertiary = TertiaryLevel::default();
    let mut quaternary = QuaternaryLevel::default();
    let mut iter = ces.iter().copied();

    loop {
        let mut ce = iter.next().expect("CE stream ends with NO_CE");
        let mut primary = (ce >> 32) as u32;
        if primary > MERGE_PRIMARY && primary < variable_limit {
            quaternary.flush_common(true);
            loop {
                if quaternary_enabled {
                    let reordered = settings.reorder(primary);
                    if reordered >> 24 >= 0x1b {
                        quaternary.bytes.push(0x1b);
                    }
                    append_weight32(&mut quaternary.bytes, reordered);
                }
                loop {
                    ce = iter.next().expect("shifted sequence ends with NO_CE");
                    primary = (ce >> 32) as u32;
                    if primary != 0 {
                        break;
                    }
                }
                if primary <= MERGE_PRIMARY || primary >= variable_limit {
                    break;
                }
            }
        }
        if primary > 1 {
            // Compressibility belongs to the original primary. Compression
            // direction and lead-byte equality use the reordered primary.
            let can_compress = compressible[(primary >> 24) as usize];
            primary = settings.reorder(primary);
            let lead = primary >> 24;
            if !can_compress || lead != previous_primary >> 24 {
                if previous_primary != 0 {
                    if primary < previous_primary {
                        if lead > 2 {
                            result.push(3);
                        }
                    } else {
                        result.push(0xff);
                    }
                }
                result.push(lead as u8);
                previous_primary = if can_compress { primary } else { 0 };
            }
            for byte in primary.to_be_bytes().into_iter().skip(1) {
                if byte == 0 {
                    break;
                }
                result.push(byte);
            }
        }
        let lower = ce as u32;
        if lower == 0 {
            continue;
        }
        if secondary_enabled {
            secondary.append(
                primary,
                lower >> 16,
                settings.options & BACKWARD_SECONDARY != 0,
            );
        }
        if case_enabled {
            cases.append(primary, lower, settings);
        }
        if tertiary_enabled {
            tertiary.append(lower, settings);
        }
        if quaternary_enabled {
            quaternary.append(lower & 0xffff, shifted);
        }
        if ce == NO_CE {
            break;
        }
    }
    if secondary_enabled {
        append_level(&mut result, secondary.bytes);
    }
    if case_enabled {
        let sentinel = cases.bytes.pop();
        debug_assert_eq!(sentinel, Some(1));
        result.push(1);
        for pair in cases.bytes.chunks(2) {
            result.push(pair[0] | pair.get(1).map_or(0, |second| second >> 4));
        }
    }
    if tertiary_enabled {
        append_level(&mut result, tertiary.bytes);
    }
    if quaternary_enabled {
        append_level(&mut result, quaternary.bytes);
    }
    if strength == Strength::Identical {
        result.push(1);
        crate::bocsu77::append_identical(identical_nfd, &mut result);
    }
    result.push(0);
    result
}

#[derive(Default)]
struct SecondaryLevel {
    bytes: Vec<u8>,
    common: usize,
    previous: u32,
    segment_start: usize,
}

impl SecondaryLevel {
    fn append(&mut self, primary: u32, weight: u32, backwards: bool) {
        if weight == 0 {
            return;
        }
        if weight == COMMON && (!backwards || primary != MERGE_PRIMARY) {
            self.common += 1;
        } else if !backwards {
            flush_common(
                &mut self.bytes,
                &mut self.common,
                weight < COMMON,
                [5, 0x25, 0x45],
                33,
            );
            append_weight16(&mut self.bytes, weight);
        } else {
            if self.common != 0 {
                self.common -= 1;
                let remainder = self.common % 33;
                self.bytes.push(if self.previous < COMMON {
                    5 + remainder as u8
                } else {
                    0x45 - remainder as u8
                });
                self.common -= remainder;
                while self.common != 0 {
                    self.bytes.push(0x25);
                    self.common -= 33;
                }
            }
            if primary > 0 && primary <= MERGE_PRIMARY {
                self.bytes[self.segment_start..].reverse();
                self.bytes.push(if primary == 1 { 1 } else { 2 });
                self.previous = 0;
                self.segment_start = self.bytes.len();
            } else {
                if weight & 0xff != 0 {
                    self.bytes.push(weight as u8);
                }
                self.bytes.push((weight >> 8) as u8);
                self.previous = weight;
            }
        }
    }
}

#[derive(Default)]
struct CaseLevel {
    bytes: Vec<u8>,
    common: usize,
}

impl CaseLevel {
    fn append(&mut self, primary: u32, lower: u32, settings: &Settings77) {
        if if settings.strength() == Strength::Primary {
            primary == 0
        } else {
            lower <= 0xffff
        } {
            return;
        }
        let mut weight = (lower >> 8) & 0xff;
        if weight & 0xc0 == 0 && weight > 1 {
            self.common += 1;
            return;
        }
        if settings.options & UPPER_FIRST == 0 {
            if self.common != 0 && (weight > 1 || !self.bytes.is_empty()) {
                self.common -= 1;
                while self.common >= 7 {
                    self.bytes.push(7 << 4);
                    self.common -= 7;
                }
                let nibble = if weight <= 1 {
                    1 + self.common
                } else {
                    13 - self.common
                };
                self.bytes.push((nibble as u8) << 4);
                self.common = 0;
            }
            if weight > 1 {
                weight = (13 + (weight >> 6)) << 4;
            }
        } else {
            if self.common != 0 {
                self.common -= 1;
                while self.common >= 13 {
                    self.bytes.push(3 << 4);
                    self.common -= 13;
                }
                self.bytes.push((3 + self.common as u8) << 4);
                self.common = 0;
            }
            if weight > 1 {
                weight = (3 - (weight >> 6)) << 4;
            }
        }
        self.bytes.push(weight as u8);
    }
}

#[derive(Default)]
struct TertiaryLevel {
    bytes: Vec<u8>,
    common: usize,
}

impl TertiaryLevel {
    fn append(&mut self, lower: u32, settings: &Settings77) {
        let mask = settings.tertiary_mask();
        let mut weight = lower & mask;
        if weight == COMMON {
            self.common += 1;
            return;
        }
        if mask & 0x8000 == 0 {
            flush_common(
                &mut self.bytes,
                &mut self.common,
                weight < COMMON,
                [5, 0x65, 0xc5],
                97,
            );
            if weight > COMMON {
                weight += 0xc000;
            }
        } else if settings.options & UPPER_FIRST == 0 {
            flush_common(
                &mut self.bytes,
                &mut self.common,
                weight < COMMON,
                [5, 0x25, 0x45],
                33,
            );
            if weight > COMMON {
                weight += 0x4000;
            }
        } else {
            if weight <= NO_CE_WEIGHT {
                // Separators keep their weights.
            } else if lower > 0xffff {
                weight ^= 0xc000;
                if weight < 0xc500 {
                    weight -= 0x4000;
                }
            } else {
                // A tertiary-only CE's artificial uppercase bits stay set.
                weight += 0x4000;
            }
            flush_common(
                &mut self.bytes,
                &mut self.common,
                weight < 0x8500,
                [0x85, 0xa5, 0xc5],
                33,
            );
        }
        append_weight16(&mut self.bytes, weight);
    }
}

#[derive(Default)]
struct QuaternaryLevel {
    bytes: Vec<u8>,
    common: usize,
}

impl QuaternaryLevel {
    fn append(&mut self, weight: u32, shifted: bool) {
        if weight & 0xc0 == 0 && weight > NO_CE_WEIGHT {
            self.common += 1;
        } else if weight == NO_CE_WEIGHT && !shifted && self.bytes.is_empty() {
            self.bytes.push(1);
        } else {
            let weight = if weight == NO_CE_WEIGHT {
                1
            } else {
                0xfc + ((weight >> 6) & 3)
            };
            self.flush_common(weight < 0x1c);
            self.bytes.push(weight as u8);
        }
    }

    fn flush_common(&mut self, following_is_lower: bool) {
        flush_common(
            &mut self.bytes,
            &mut self.common,
            following_is_lower,
            [0x1c, 0x8c, 0xfc],
            113,
        );
    }
}

fn append_level(output: &mut Vec<u8>, mut level: Vec<u8>) {
    let sentinel = level.pop();
    debug_assert_eq!(sentinel, Some(1));
    output.push(1);
    output.extend_from_slice(&level);
}

fn append_weight16(output: &mut Vec<u8>, weight: u32) {
    debug_assert_ne!(weight & 0xffff, 0);
    output.push((weight >> 8) as u8);
    if weight & 0xff != 0 {
        output.push(weight as u8);
    }
}

fn append_weight32(output: &mut Vec<u8>, weight: u32) {
    for byte in weight.to_be_bytes() {
        if byte == 0 {
            break;
        }
        output.push(byte);
    }
}

fn flush_common(
    output: &mut Vec<u8>,
    count: &mut usize,
    following_is_lower: bool,
    [low, middle, high]: [u8; 3],
    max_count: usize,
) {
    if *count == 0 {
        return;
    }
    *count -= 1;
    while *count >= max_count {
        output.push(middle);
        *count -= max_count;
    }
    output.push(if following_is_lower {
        low + *count as u8
    } else {
        high - *count as u8
    });
    *count = 0;
}
