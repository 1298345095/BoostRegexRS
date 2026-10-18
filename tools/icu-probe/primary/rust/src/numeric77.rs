// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2010-2014, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 CollationIterator::appendNumericSegmentCEs.
// See ../NOTICE.md, ../LOCALE-MECHANISMS.md and ../../data/LICENSE-ICU.txt.

//! Dense and pair/exponent encodings for a complete collected digit sequence.

pub(crate) fn numeric_ces(digits: &[u8], numeric_primary: u32) -> Vec<u64> {
    debug_assert!(!digits.is_empty());
    debug_assert!(digits.iter().all(|digit| *digit <= 9));
    let mut ces = Vec::new();
    let mut pos = 0;
    while pos < digits.len() {
        while pos < digits.len() - 1 && digits[pos] == 0 {
            pos += 1;
        }
        let limit = digits.len().min(pos + 254);
        append_segment(&digits[pos..limit], numeric_primary, &mut ces);
        pos = limit;
    }
    ces
}

fn append_segment(digits: &[u8], numeric_primary: u32, output: &mut Vec<u64>) {
    let mut length = digits.len();
    debug_assert!((1..=254).contains(&length));
    debug_assert!(length == 1 || digits[0] != 0);
    if length <= 7 {
        let mut value = digits
            .iter()
            .fold(0_u32, |value, digit| value * 10 + u32::from(*digit));
        if value < 74 {
            output.push(make_ce(numeric_primary | ((2 + value) << 16)));
            return;
        }
        value -= 74;
        if value < 40 * 254 {
            output.push(make_ce(
                numeric_primary | ((76 + value / 254) << 16) | ((2 + value % 254) << 8),
            ));
            return;
        }
        value -= 40 * 254;
        if value < 16 * 254 * 254 {
            let mut primary = numeric_primary | (2 + value % 254);
            value /= 254;
            primary |= (2 + value % 254) << 8;
            value /= 254;
            primary |= (116 + value % 254) << 16;
            output.push(make_ce(primary));
            return;
        }
    }
    // Exponent records the original number of pairs, before trailing 00 pairs
    // are omitted. At least the first nonzero digit remains after trimming.
    let pairs = length.div_ceil(2);
    let mut primary = numeric_primary | ((128 + pairs as u32) << 16);
    while digits[length - 1] == 0 && digits[length - 2] == 0 {
        length -= 2;
    }
    let (mut pair, mut pos) = if length & 1 != 0 {
        (u32::from(digits[0]), 1)
    } else {
        (u32::from(digits[0]) * 10 + u32::from(digits[1]), 2)
    };
    pair = 11 + 2 * pair;
    let mut shift = 8;
    while pos < length {
        if shift == 0 {
            primary |= pair;
            output.push(make_ce(primary));
            primary = numeric_primary;
            shift = 16;
        } else {
            primary |= pair << shift;
            shift -= 8;
        }
        pair = 11 + 2 * (u32::from(digits[pos]) * 10 + u32::from(digits[pos + 1]));
        pos += 2;
    }
    primary |= (pair - 1) << shift;
    output.push(make_ce(primary));
}

fn make_ce(primary: u32) -> u64 {
    (u64::from(primary) << 32) | 0x0500_0500
}
