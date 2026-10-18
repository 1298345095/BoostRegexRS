//! Regression expectations were checked against the official ICU4C 77.1 and
//! Boost.Regex 1.89.0 development references. They are test fixtures only; the
//! implementation never reads expected keys or recognizes these input strings.

use std::sync::OnceLock;

use icu77_root_primary::{Data77, Error, RootPrimary};

const DATA: &[u8] = include_bytes!("../../data/root-icu77.bin");

fn collator() -> &'static RootPrimary {
    static COLLATOR: OnceLock<RootPrimary> = OnceLock::new();
    COLLATOR.get_or_init(|| RootPrimary::new(Data77::from_bytes(DATA).expect("fixed data")))
}

fn key(input: &str) -> Vec<u8> {
    collator()
        .primary_utf8(input, false)
        .expect("supported input")
        .raw_icu
}

#[test]
fn empty_and_primary_ignorables_keep_one_zero() {
    for text in ["", "\0", "\0\0", "\u{0301}\u{0315}\u{0327}\u{200b}\u{feff}"] {
        let result = collator().primary_utf8(text, false).unwrap();
        assert_eq!(result.raw_icu, [0]);
        assert_eq!(result.boost, [0]);
    }
    assert_eq!(key("a\0b"), [0x2b, 0x2d, 0]);
    assert_eq!(
        collator().primary_utf8("a\0b", false).unwrap().boost,
        [0x2b, 0x2d]
    );
}

#[test]
fn primary_compression_terminates_in_both_directions_and_at_merge() {
    assert_eq!(
        key("αβаб一"),
        [0x61, 6, 8, 0xff, 0x62, 6, 0x0c, 0xff, 0xfa, 2, 2, 0]
    );
    assert_eq!(
        key("一баβαa"),
        [0xfa, 2, 2, 0x62, 0x0c, 6, 3, 0x61, 8, 6, 3, 0x2b, 0]
    );
    assert_eq!(key("α\u{fffe}β"), [0x61, 6, 2, 0x61, 8, 0]);
    assert_eq!(key("α"), [0x61, 6, 0]);
}

#[test]
fn prefix_uses_the_actual_preceding_character() {
    assert_eq!(key("l·"), [0x41, 0]);
    assert_eq!(key("L\u{0387}"), [0x41, 0]);
    assert_eq!(key("a·"), [0x2b, 0x09, 0x1a, 0]);
    assert_ne!(key("l\0·"), key("l·"));
    let traced = collator().primary_utf8("l·", true).unwrap();
    assert!(
        traced
            .trace
            .unwrap()
            .iter()
            .any(|event| event.kind == "prefix")
    );
}

#[test]
fn discontiguous_contraction_observes_blocking_and_emits_skipped_marks() {
    // Cyrillic i + cedilla(CCC202) + breve(CCC230) can match short i.
    let result = collator().primary_utf8("и\u{0327}\u{0306}", true).unwrap();
    assert_eq!(result.raw_icu, [0x62, 0x4e, 0]);
    assert_eq!(result.raw_icu, key("й"));
    assert_eq!(
        result.ces.unwrap(),
        [0x624e000005000500, 0x00000000a0000500, 0x0000000101000100]
    );
    assert!(
        result
            .trace
            .unwrap()
            .iter()
            .any(|event| event.kind == "discontiguous_match")
    );
    // Acute(CCC230) blocks breve(CCC230); a starter blocks it as well.
    assert_eq!(key("и\u{0301}\u{0306}"), [0x62, 0x46, 0]);
    assert_ne!(key("иa\u{0306}"), key("йa"));
}

#[test]
fn ce_trace_preserves_non_fcd_order_even_when_primary_keys_agree() {
    // Checked with trace-root --utf16 0061,0315,0300. Always pre-NFD would
    // silently change these CEs while still passing this PRIMARY key example.
    let original = collator().primary_utf8("a\u{0315}\u{0300}", true).unwrap();
    let reordered = collator().primary_utf8("a\u{0300}\u{0315}", true).unwrap();
    assert_eq!(original.raw_icu, reordered.raw_icu);
    assert_eq!(
        original.ces.unwrap(),
        [
            0x2b00000005000500,
            0x00000000a6000500,
            0x000000008a000500,
            0x0000000101000100,
        ]
    );
    assert_eq!(
        reordered.ces.unwrap(),
        [
            0x2b00000005000500,
            0x000000008a000500,
            0x00000000a6000500,
            0x0000000101000100,
        ]
    );
}

#[test]
fn hangul_jamo_and_expansions_use_complete_table_mappings() {
    for (composed, decomposed) in [
        ("가", "\u{1100}\u{1161}"),
        ("각", "\u{1100}\u{1161}\u{11a8}"),
        ("힣", "\u{1112}\u{1175}\u{11c2}"),
    ] {
        assert_eq!(key(composed), key(decomposed));
    }
    assert_eq!(key("ß"), [0x4f, 0x4f, 0]);
    assert_eq!(key("ﬃ"), key("ffi"));
    assert_eq!(key("一"), [0xfa, 2, 2, 0]);
}

#[test]
fn long_keys_cross_boost_stack_buffer_without_truncation() {
    for length in [97, 98, 99, 100, 101, 4096, 10000] {
        let result = collator().primary_utf8(&"a".repeat(length), false).unwrap();
        assert_eq!(result.raw_icu.len(), length + 1);
        assert_eq!(result.boost.len(), length);
        assert!(result.boost.iter().all(|weight| *weight == 0x2b));
        assert_eq!(result.raw_icu.last(), Some(&0));
    }
    assert_eq!(key(&"α".repeat(4096)).len(), 4098);
}

#[test]
fn checked_input_adapters_keep_units_and_reject_invalid_surrogates() {
    let text = "\0a😀\u{10ffff}각一\0";
    let expected = collator().primary_utf8(text, false).unwrap();
    assert_eq!(
        collator()
            .primary_u32(&text.chars().map(u32::from).collect::<Vec<_>>(), false)
            .unwrap(),
        expected
    );
    assert_eq!(
        collator()
            .primary_utf16(&text.encode_utf16().collect::<Vec<_>>(), false)
            .unwrap(),
        expected
    );
    for value in [0xd800, 0xdfff, 0x110000, u32::MAX] {
        assert_eq!(
            collator().primary_u32(&[0x61, value], false),
            Err(Error::InvalidUtf32 { position: 1, value })
        );
    }
    assert_eq!(
        collator().primary_utf16(&[0x61, 0xd800, 0x62], false),
        Err(Error::InvalidUtf16 {
            position: 1,
            value: 0xd800
        })
    );
    assert_eq!(
        collator().primary_utf16(&[0x61, 0xdc00], false),
        Err(Error::InvalidUtf16 {
            position: 1,
            value: 0xdc00
        })
    );
    // Raw ICU diagnostic is a separate method and must not substitute U+FFFD.
    assert_ne!(
        collator()
            .primary_icu_utf16(&[0xd800], false)
            .unwrap()
            .raw_icu,
        key("�")
    );
}

#[test]
fn data_identity_and_settings_are_checked_before_running() {
    assert_eq!(collator().data().primary_options, 16);
    let mut wrong = DATA.to_vec();
    wrong[12] = 78;
    assert!(Data77::from_bytes(&wrong).is_err());
    let mut normalization_on = DATA.to_vec();
    normalization_on[36] |= 1;
    assert!(Data77::from_bytes(&normalization_on).is_err());
    assert!(Data77::from_bytes(&DATA[..DATA.len() - 1]).is_err());
    let mut trailing = DATA.to_vec();
    trailing.push(0);
    assert!(Data77::from_bytes(&trailing).is_err());
}
