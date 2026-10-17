// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2012-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// PRIMARY-only Rust adaptation of ICU77 collationkeys.cpp.
// See ../NOTICE.md and ../../data/LICENSE-ICU.txt.

//! ICU PRIMARY bytes and Boost's byte-per-u32 return convention.

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
