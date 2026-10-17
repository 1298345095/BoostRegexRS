//! Full-key fixtures come from the fixed ICU77 / Boost.Regex 1.89.0 oracle.
//! Empty input uses only the approved ADR-0005 valid-pointer expectation.
//! Runtime code never reads these fixtures or recognizes their input strings.

use std::sync::OnceLock;

use icu77_root_primary::{Data77, Error, NfdData77, RootCollator, RootPrimary};

const DATA: &[u8] = include_bytes!("../../data/root-icu77.bin");
const NFD: &[u8] = include_bytes!("../../data/root-icu77-nfd.bin");

fn collator() -> &'static RootCollator {
    static COLLATOR: OnceLock<RootCollator> = OnceLock::new();
    COLLATOR.get_or_init(|| {
        RootCollator::new(
            Data77::from_bytes(DATA).unwrap(),
            NfdData77::from_bytes(NFD).unwrap(),
        )
        .unwrap()
    })
}

#[test]
fn official_full_keys_cover_level_compression_and_signed_bocsu_boundaries() {
    let fixture = include_str!("data/identical.tsv");
    let mut count = 0;
    for line in fixture.lines().skip(1) {
        let columns = line.split('\t').collect::<Vec<_>>();
        assert_eq!(columns.len(), 4);
        let input = (0..columns[1].len())
            .step_by(2)
            .map(|index| u8::from_str_radix(&columns[1][index..index + 2], 16).unwrap())
            .collect::<Vec<_>>();
        let expected_raw = columns[2]
            .split(',')
            .map(|value| u8::from_str_radix(value, 16).unwrap())
            .collect::<Vec<_>>();
        let expected_boost = columns[3]
            .split(',')
            .map(|value| u32::from_str_radix(value, 16).unwrap())
            .collect::<Vec<_>>();
        let actual = collator()
            .identical_utf8(std::str::from_utf8(&input).unwrap(), false)
            .unwrap();
        assert_eq!(actual.raw_icu, expected_raw, "{} raw ICU bytes", columns[0]);
        assert_eq!(
            actual.boost, expected_boost,
            "{} Boost elements",
            columns[0]
        );
        count += 1;
    }
    assert_eq!(count, 167);
}

#[test]
fn empty_uses_approved_key_and_nul_is_retained_in_identical_level() {
    let empty = collator().identical_utf8("", false).unwrap();
    assert_eq!(empty.raw_icu, [1, 1, 1, 1, 0]);
    assert_eq!(empty.boost, [1, 1, 1, 1]);
    let nul = collator().identical_utf8("\0", false).unwrap();
    assert_eq!(nul.raw_icu, [1, 1, 1, 1, 0x31, 0]);
    assert_eq!(nul.boost, [1, 1, 1, 1, 0x31]);
    assert_ne!(
        collator().identical_utf8("a\0b", false).unwrap().raw_icu,
        collator().identical_utf8("ab", false).unwrap().raw_icu
    );
}

#[test]
fn nfd_tail_does_not_normalize_the_ce_input() {
    let original = collator()
        .identical_utf8("a\u{0315}\u{0300}", true)
        .unwrap();
    let reordered = collator()
        .identical_utf8("a\u{0300}\u{0315}", true)
        .unwrap();
    assert_eq!(original.identical_nfd, Some(vec![0x61, 0x300, 0x315]));
    assert_eq!(original.identical_nfd, reordered.identical_nfd);
    assert_eq!(
        original.raw_icu,
        [
            0x2b, 1, 0x45, 0xa6, 0x8a, 1, 7, 1, 1, 0x92, 0xd4, 0xb9, 0x46, 0
        ]
    );
    assert_ne!(original.raw_icu, reordered.raw_icu);
    assert_eq!(
        original.ces,
        collator()
            .primary_utf8("a\u{0315}\u{0300}", true)
            .unwrap()
            .ces
    );
    assert_ne!(original.ces, reordered.ces);
}

#[test]
fn nfd_is_recursive_stable_and_canonical_without_compatibility_decomposition() {
    for (input, expected) in [
        ("é", vec![0x65, 0x301]),
        ("\u{1f82}", vec![0x3b1, 0x313, 0x300, 0x345]),
        ("각", vec![0x1100, 0x1161, 0x11a8]),
        ("\u{212b}\u{0301}", vec![0x41, 0x30a, 0x301]),
        ("\u{0345}\u{0301}\u{0323}", vec![0x323, 0x301, 0x345]),
        ("a\u{0301}\u{0300}", vec![0x61, 0x301, 0x300]),
        ("a\u{0315}\0\u{0300}", vec![0x61, 0x315, 0, 0x300]),
        ("ﬃ", vec![0xfb03]),
    ] {
        assert_eq!(
            collator()
                .identical_utf8(input, true)
                .unwrap()
                .identical_nfd,
            Some(expected),
            "{input:?}"
        );
    }
    assert_eq!(
        collator().identical_utf8("é", false).unwrap().raw_icu,
        collator()
            .identical_utf8("e\u{0301}", false)
            .unwrap()
            .raw_icu
    );
    assert_eq!(
        collator().identical_utf8("각", false).unwrap().raw_icu,
        collator()
            .identical_utf8("\u{1100}\u{1161}\u{11a8}", false)
            .unwrap()
            .raw_icu
    );
    assert_ne!(
        collator().identical_utf8("ﬃ", false).unwrap().raw_icu,
        collator().identical_utf8("ffi", false).unwrap().raw_icu
    );
}

#[test]
fn identical_checked_adapters_preserve_original_input_positions() {
    let text = "\0a😀\u{10ffff}각一\0";
    let expected = collator().identical_utf8(text, false).unwrap();
    assert_eq!(
        collator()
            .identical_u32(&text.chars().map(u32::from).collect::<Vec<_>>(), false)
            .unwrap(),
        expected
    );
    assert_eq!(
        collator()
            .identical_utf16(&text.encode_utf16().collect::<Vec<_>>(), false)
            .unwrap(),
        expected
    );
    assert_eq!(
        collator().identical_u32(&[0x1f600, 0xd800], false),
        Err(Error::InvalidUtf32 {
            position: 1,
            value: 0xd800
        })
    );
    assert_eq!(
        collator().identical_utf16(&[0xd83d, 0xde00, 0xd800], false),
        Err(Error::InvalidUtf16 {
            position: 2,
            value: 0xd800
        })
    );
    assert_ne!(
        collator()
            .identical_icu_utf16(&[0xd800], false)
            .unwrap()
            .raw_icu,
        collator().identical_utf8("�", false).unwrap().raw_icu
    );
}

#[test]
fn additional_data_and_default_settings_are_validated() {
    let mut wrong_version = NFD.to_vec();
    wrong_version[20] = 17;
    assert!(NfdData77::from_bytes(&wrong_version).is_err());
    assert!(NfdData77::from_bytes(&NFD[..NFD.len() - 1]).is_err());
    let mut trailing = NFD.to_vec();
    trailing.push(0);
    assert!(NfdData77::from_bytes(&trailing).is_err());
    // PRIMARY does not use backward secondary; IDENTICAL must reject that
    // different setting instead of silently applying root's forward writer.
    let mut backwards = DATA.to_vec();
    backwards[37] |= 8;
    assert!(
        RootCollator::new(
            Data77::from_bytes(&backwards).unwrap(),
            NfdData77::from_bytes(NFD).unwrap()
        )
        .is_err()
    );
}

#[test]
fn primary_results_are_unchanged_through_the_combined_collator() {
    let primary = RootPrimary::new(Data77::from_bytes(DATA).unwrap());
    for input in [
        "",
        "\0",
        "a\u{0315}\u{0300}",
        "l·",
        "и\u{0327}\u{0306}",
        "각😀一\u{fffe}β",
    ] {
        assert_eq!(
            collator().primary_utf8(input, true).unwrap(),
            primary.primary_utf8(input, true).unwrap()
        );
    }
}
