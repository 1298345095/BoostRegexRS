// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2001-2014, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 bocsu.cpp / bocsu.h.
// See ../NOTICE.md and ../../data/LICENSE-ICU.txt.

//! ICU's Binary Ordered Compression Scheme for Unicode IDENTICAL levels.

const MIN: i32 = 3;
const MIDDLE: i32 = 0x81;
const TAIL_COUNT: i32 = 253;
const REACH_POS_1: i32 = 80;
const REACH_NEG_1: i32 = -REACH_POS_1;
const REACH_POS_2: i32 = 42 * TAIL_COUNT + 41;
const REACH_NEG_2: i32 = -REACH_POS_2 - 1;
const REACH_POS_3: i32 = 3 * TAIL_COUNT * TAIL_COUNT + 2 * TAIL_COUNT + TAIL_COUNT - 1;
const REACH_NEG_3: i32 = -REACH_POS_3 - 1;
const START_POS_2: i32 = MIDDLE + REACH_POS_1 + 1;
const START_POS_3: i32 = START_POS_2 + 42;
const START_NEG_2: i32 = MIDDLE + REACH_NEG_1;
const START_NEG_3: i32 = START_NEG_2 - 42;

pub(crate) fn append_identical(nfd: &[u32], output: &mut Vec<u8>) {
    let mut previous = 0_i32;
    for &cp in nfd {
        previous = if (0x4e00..0xa000).contains(&previous) {
            0x9fff - REACH_POS_2
        } else {
            (previous & !0x7f) - REACH_NEG_1
        };
        if cp == 0xfffe {
            output.push(2);
            previous = 0;
        } else {
            append_difference(cp as i32 - previous, output);
            previous = cp as i32;
        }
    }
}

fn append_difference(mut diff: i32, output: &mut Vec<u8>) {
    if diff >= REACH_NEG_1 {
        if diff <= REACH_POS_1 {
            output.push((MIDDLE + diff) as u8);
        } else if diff <= REACH_POS_2 {
            output.push((START_POS_2 + diff / TAIL_COUNT) as u8);
            output.push((MIN + diff % TAIL_COUNT) as u8);
        } else if diff <= REACH_POS_3 {
            let last = (MIN + diff % TAIL_COUNT) as u8;
            diff /= TAIL_COUNT;
            let middle = (MIN + diff % TAIL_COUNT) as u8;
            output.extend_from_slice(&[(START_POS_3 + diff / TAIL_COUNT) as u8, middle, last]);
        } else {
            let last = (MIN + diff % TAIL_COUNT) as u8;
            diff /= TAIL_COUNT;
            let middle = (MIN + diff % TAIL_COUNT) as u8;
            diff /= TAIL_COUNT;
            output.extend_from_slice(&[0xff, (MIN + diff % TAIL_COUNT) as u8, middle, last]);
        }
    } else if diff >= REACH_NEG_2 {
        output.push((START_NEG_2 + diff.div_euclid(TAIL_COUNT)) as u8);
        output.push((MIN + diff.rem_euclid(TAIL_COUNT)) as u8);
    } else if diff >= REACH_NEG_3 {
        // ICU's NEGDIVMOD computes floor division and a non-negative remainder.
        let last = (MIN + diff.rem_euclid(TAIL_COUNT)) as u8;
        diff = diff.div_euclid(TAIL_COUNT);
        let middle = (MIN + diff.rem_euclid(TAIL_COUNT)) as u8;
        output.extend_from_slice(&[
            (START_NEG_3 + diff.div_euclid(TAIL_COUNT)) as u8,
            middle,
            last,
        ]);
    } else {
        let last = (MIN + diff.rem_euclid(TAIL_COUNT)) as u8;
        diff = diff.div_euclid(TAIL_COUNT);
        let middle = (MIN + diff.rem_euclid(TAIL_COUNT)) as u8;
        diff = diff.div_euclid(TAIL_COUNT);
        output.extend_from_slice(&[
            MIN as u8,
            (MIN + diff.rem_euclid(TAIL_COUNT)) as u8,
            middle,
            last,
        ]);
    }
}
