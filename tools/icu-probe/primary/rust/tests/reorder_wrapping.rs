use icu77_root_primary::{
    Collator77, Data77, NfdData77, Reordering77, ScriptGroups77, Settings77, Strength,
};
use std::sync::Arc;

const NATIVE: &[u8] = include_bytes!("data/reorder77/wrapped-settings.bin");

#[test]
fn native_wrapping_fields_are_preserved_and_corruption_is_rejected() {
    let settings = Settings77::from_bytes(NATIVE).unwrap();
    let expected = settings.reordering().unwrap();
    let groups =
        ScriptGroups77::from_bytes(include_bytes!("../../data/locales/scripts.bin")).unwrap();
    let generated = groups.make_reordering(expected.codes()).unwrap().unwrap();
    assert_eq!(&generated, expected);
    assert_eq!(expected.table()[0xfd], 0xff);
    assert_eq!(expected.table()[0xfe], 0);

    // A legitimate wrapped zero is justified by the complete native format;
    // it does not authorize dropping the actual retained ranges.
    assert!(
        Reordering77::from_icu(
            expected.codes().to_vec(),
            *expected.table(),
            expected.min_high_no_reorder(),
            Vec::new(),
        )
        .is_err()
    );
    let mut table = *expected.table();
    table[0x33] = 0;
    assert!(
        Reordering77::from_icu(
            expected.codes().to_vec(),
            table,
            expected.min_high_no_reorder(),
            expected.ranges().to_vec(),
        )
        .is_err()
    );
}

#[test]
fn wrapped_public_setter_matches_complete_native_keys_at_every_strength() {
    let groups =
        ScriptGroups77::from_bytes(include_bytes!("../../data/locales/scripts.bin")).unwrap();
    let expected = Settings77::from_bytes(NATIVE).unwrap();
    let defaults =
        Settings77::from_bytes(include_bytes!("../../data/locales/settings-0000.bin")).unwrap();
    let mut settings = defaults.clone();
    settings
        .set_reordering(&groups, expected.reordering().unwrap().codes(), &defaults)
        .unwrap();
    let data = Arc::new(Data77::from_bytes(include_bytes!("../../data/root-icu77.bin")).unwrap());
    let nfd =
        Arc::new(NfdData77::from_bytes(include_bytes!("../../data/root-icu77-nfd.bin")).unwrap());
    let mut collator = Collator77::new(data, nfd, settings);
    let mut rows = include_str!("data/reorder77/wrapped-a-keys.tsv").lines();
    assert_eq!(rows.next(), Some("strength\traw_icu_hex"));
    let strengths = [
        Strength::Primary,
        Strength::Secondary,
        Strength::Tertiary,
        Strength::Quaternary,
        Strength::Identical,
    ];
    for strength in strengths {
        let (name, raw) = rows.next().unwrap().split_once('\t').unwrap();
        assert_eq!(name, strength.name());
        let (pairs, remainder) = raw.as_bytes().as_chunks::<2>();
        assert!(remainder.is_empty());
        let reference: Vec<_> = pairs
            .iter()
            .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
            .collect();
        collator.settings_mut().set_strength(strength);
        assert_eq!(
            collator.sort_key_utf16(&[0x61], false).unwrap().raw_icu,
            reference
        );
    }
    assert!(rows.next().is_none());
}
