// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2012-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 collationkeys.cpp for root default settings.
// See ../NOTICE.md and ../../data/LICENSE-ICU.txt.

//! ICU PRIMARY/IDENTICAL bytes and Boost's byte-per-u32 return convention.

use crate::ce77::NO_CE;

pub(crate) fn primary_bytes(ces: &[u64], compressible: &[bool; 256]) -> Vec<u8> {
    let mut result = Vec::new();
    let mut previous_primary = 0;
    for ce in ces {
        if *ce == NO_CE {
            break;
        }
        let primary = (ce >> 32) as u32;
        if primary <= 1 {
            continue;
        }
        let lead = primary >> 24;
        let can_compress = compressible[lead as usize];
        if !can_compress || lead != previous_primary >> 24 {
            if previous_primary != 0 {
                if primary < previous_primary {
                    // No low terminator at a merge segment boundary (U+FFFE).
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
    // ICU ends PRIMARY directly with zero; an open compression run does not
    // receive an extra low terminator when the end-of-input CE is reached.
    result.push(0);
    result
}

/// Write the levels selected by root IDENTICAL's default options (0xf010).
/// Case level/first and backwards-secondary are OFF; alternate is non-ignorable.
pub(crate) fn identical_bytes(ces: &[u64], compressible: &[bool; 256], nfd: &[u32]) -> Vec<u8> {
    const COMMON_WEIGHT: u32 = 0x0500;
    const NO_CE_WEIGHT: u32 = 0x0100;
    const ONLY_TERTIARY_MASK: u32 = 0x3f3f;

    let mut result = primary_bytes(ces, compressible);
    result.pop(); // Other levels replace PRIMARY's final NUL.
    let mut secondaries = Vec::new();
    let mut tertiaries = Vec::new();
    let mut quaternaries = Vec::new();
    let mut common_secondaries = 0;
    let mut common_tertiaries = 0;
    let mut common_quaternaries = 0;

    for &ce in ces {
        let lower = ce as u32;
        if lower == 0 {
            continue;
        }
        let secondary = lower >> 16;
        if secondary == COMMON_WEIGHT {
            common_secondaries += 1;
        } else if secondary != 0 {
            flush_common(
                &mut common_secondaries,
                &mut secondaries,
                secondary < COMMON_WEIGHT,
                [0x05, 0x25, 0x45],
                33,
            );
            append_weight16(&mut secondaries, secondary);
        }

        // Default caseFirst=OFF removes the dedicated case bits. The ordinary
        // tertiary weights still distinguish upper/lower and other variants.
        let mut tertiary = lower & ONLY_TERTIARY_MASK;
        if tertiary == COMMON_WEIGHT {
            common_tertiaries += 1;
        } else {
            flush_common(
                &mut common_tertiaries,
                &mut tertiaries,
                tertiary < COMMON_WEIGHT,
                [0x05, 0x65, 0xc5],
                97,
            );
            if tertiary > COMMON_WEIGHT {
                tertiary += 0xc000;
            }
            append_weight16(&mut tertiaries, tertiary);
        }

        let mut quaternary = lower & 0xffff;
        if quaternary & 0xc0 == 0 && quaternary > NO_CE_WEIGHT {
            common_quaternaries += 1;
        } else if quaternary == NO_CE_WEIGHT && quaternaries.is_empty() {
            // With non-ignorable alternate handling, an all-common level is
            // omitted: its length distinction is already in tertiary weights.
            quaternaries.push(1);
        } else {
            quaternary = if quaternary == NO_CE_WEIGHT {
                1
            } else {
                0xfc + ((quaternary >> 6) & 3)
            };
            flush_common(
                &mut common_quaternaries,
                &mut quaternaries,
                quaternary < 0x1c,
                [0x1c, 0x8c, 0xfc],
                113,
            );
            quaternaries.push(quaternary as u8);
        }
        if ce == NO_CE {
            break;
        }
    }
    // Each level's sentinel byte terminates common-weight compression but is
    // not copied. The next level contributes its own leading separator.
    for mut level in [secondaries, tertiaries, quaternaries] {
        let sentinel = level.pop();
        debug_assert_eq!(sentinel, Some(1));
        result.push(1);
        result.extend_from_slice(&level);
    }
    result.push(1);
    crate::bocsu77::append_identical(nfd, &mut result);
    result.push(0);
    result
}

fn append_weight16(output: &mut Vec<u8>, weight: u32) {
    debug_assert_ne!(weight & 0xffff, 0);
    output.push((weight >> 8) as u8);
    if weight & 0xff != 0 {
        output.push(weight as u8);
    }
}

fn flush_common(
    count: &mut usize,
    output: &mut Vec<u8>,
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

/// Each byte becomes one u32. Only a terminator following other bytes is removed.
pub fn boost_key(raw_icu: &[u8]) -> Vec<u32> {
    let length = if raw_icu.len() > 1 && raw_icu.last() == Some(&0) {
        raw_icu.len() - 1
    } else {
        raw_icu.len()
    };
    raw_icu[..length]
        .iter()
        .map(|byte| u32::from(*byte))
        .collect()
}
