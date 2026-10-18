//! Mechanism tests use fixed official data and reference-generated full keys.
//! No expected input/key pairs are part of runtime code or data loaders.

use std::path::PathBuf;
use std::sync::{Arc, OnceLock};

use icu77_root_primary::{
    Collator77, Data77, Error, NfdData77, ScriptGroups77, Settings77, Strength,
};

fn root_data() -> Arc<Data77> {
    static DATA: OnceLock<Arc<Data77>> = OnceLock::new();
    Arc::clone(DATA.get_or_init(|| {
        Arc::new(Data77::from_bytes(include_bytes!("../../data/root-icu77.bin")).unwrap())
    }))
}

fn nfd_data() -> Arc<NfdData77> {
    static DATA: OnceLock<Arc<NfdData77>> = OnceLock::new();
    Arc::clone(DATA.get_or_init(|| {
        Arc::new(NfdData77::from_bytes(include_bytes!("../../data/root-icu77-nfd.bin")).unwrap())
    }))
}

fn root_with_options(options: u32) -> Collator77 {
    Collator77::new(
        root_data(),
        nfd_data(),
        Settings77::from_icu(options, 0x0bff_ffff, None).unwrap(),
    )
}

fn locale_directory() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../data/locales")
}

fn exported_paths(prefix: &str) -> Vec<PathBuf> {
    let mut paths = std::fs::read_dir(locale_directory())
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with(prefix) && name.ends_with(".bin"))
        })
        .collect::<Vec<_>>();
    paths.sort();
    paths
}

#[test]
fn complete_settings_writer_retains_the_official_root_key_fixtures() {
    let collator = root_with_options(0xf010);
    let fixture = include_str!("data/identical.tsv");
    let mut count = 0;
    for line in fixture.lines().skip(1) {
        let fields = line.split('\t').collect::<Vec<_>>();
        let bytes = (0..fields[1].len())
            .step_by(2)
            .map(|index| u8::from_str_radix(&fields[1][index..index + 2], 16).unwrap())
            .collect::<Vec<_>>();
        let expected_raw = fields[2]
            .split(',')
            .map(|value| u8::from_str_radix(value, 16).unwrap())
            .collect::<Vec<_>>();
        let expected_boost = fields[3]
            .split(',')
            .map(|value| u32::from_str_radix(value, 16).unwrap())
            .collect::<Vec<_>>();
        let actual = collator
            .sort_key_utf8(std::str::from_utf8(&bytes).unwrap(), false)
            .unwrap();
        assert_eq!(actual.raw_icu, expected_raw, "{} raw ICU", fields[0]);
        assert_eq!(actual.boost, expected_boost, "{} Boost u32", fields[0]);
        count += 1;
    }
    assert_eq!(count, 167);
}

#[test]
fn every_strength_ends_after_its_selected_level() {
    // These level prefixes come from the existing official ICU77 IDENTICAL
    // fixture for "a". BOCSU is included only at IDENTICAL strength.
    for (strength, expected) in [
        (Strength::Primary, vec![0x2b, 0]),
        (Strength::Secondary, vec![0x2b, 1, 5, 0]),
        (Strength::Tertiary, vec![0x2b, 1, 5, 1, 5, 0]),
        (Strength::Quaternary, vec![0x2b, 1, 5, 1, 5, 1, 0]),
        (Strength::Identical, vec![0x2b, 1, 5, 1, 5, 1, 1, 0x92, 0]),
    ] {
        let mut collator = root_with_options(0x2010);
        collator.settings_mut().set_strength(strength);
        assert_eq!(
            collator.sort_key_utf8("a", false).unwrap().raw_icu,
            expected
        );
    }
}

#[test]
fn fcd_and_numeric_settings_preserve_original_invalid_input_positions() {
    let collator = root_with_options(0xf013);
    assert_eq!(
        collator.sort_key_u32(&[0x1f600, 0x31, 0xd800], true),
        Err(Error::InvalidUtf32 {
            position: 2,
            value: 0xd800
        }),
    );
    assert_eq!(
        collator.sort_key_utf16(&[0xd83d, 0xde00, 0x31, 0xd800], true),
        Err(Error::InvalidUtf16 {
            position: 3,
            value: 0xd800
        }),
    );
    let text = "1\0é😀\u{0315}\u{0300}";
    let expected = collator.sort_key_utf8(text, true).unwrap();
    assert_eq!(
        collator
            .sort_key_u32(&text.chars().map(u32::from).collect::<Vec<_>>(), true)
            .unwrap(),
        expected
    );
    assert_eq!(
        collator
            .sort_key_utf16(&text.encode_utf16().collect::<Vec<_>>(), true)
            .unwrap(),
        expected
    );
}

#[test]
fn all_published_tailoring_owners_load_against_the_original_root() {
    let paths = exported_paths("owner-");
    assert_eq!(paths.len(), 129);
    for path in paths {
        Data77::from_owner_bytes(&std::fs::read(&path).unwrap(), root_data())
            .unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    }
}

#[test]
fn public_reorder_codes_reproduce_every_exported_reorder_table_and_split_range() {
    let groups =
        ScriptGroups77::from_bytes(&std::fs::read(locale_directory().join("scripts.bin")).unwrap())
            .unwrap();
    let paths = exported_paths("settings-");
    assert_eq!(paths.len(), 432);
    let mut reordered = 0;
    let mut split = 0;
    for path in paths {
        let settings = Settings77::from_bytes(&std::fs::read(&path).unwrap())
            .unwrap_or_else(|error| panic!("{}: {error}", path.display()));
        let Some(expected) = settings.reordering() else {
            continue;
        };
        let actual = groups
            .make_reordering(expected.codes())
            .unwrap_or_else(|error| panic!("{}: {error}", path.display()))
            .unwrap();
        assert_eq!(actual.codes(), expected.codes(), "{} codes", path.display());
        assert_eq!(
            actual.table(),
            expected.table(),
            "{} lead table",
            path.display()
        );
        assert_eq!(
            actual.ranges(),
            expected.ranges(),
            "{} split ranges",
            path.display()
        );
        // ICU aliasReordering sets the unused minimum to zero when no lead is
        // split; setReordering retains its last full range limit. Both execute
        // entirely through the identical lead table in that case.
        if !expected.ranges().is_empty() {
            assert_eq!(
                actual.min_high_no_reorder(),
                expected.min_high_no_reorder(),
                "{} split minimum",
                path.display()
            );
            split += 1;
        }
        reordered += 1;
    }
    assert!(reordered >= 20);
    assert!(split >= 6);
}

#[test]
fn reorder_reset_and_error_paths_preserve_effective_settings() {
    let groups =
        ScriptGroups77::from_bytes(&std::fs::read(locale_directory().join("scripts.bin")).unwrap())
            .unwrap();
    let defaults = Settings77::from_icu(
        0x2010,
        0x0bff_ffff,
        groups.make_reordering(&[14, 25]).unwrap(),
    )
    .unwrap();
    let mut settings = defaults.clone();
    for codes in [&[][..], &[103][..]] {
        settings.set_reordering(&groups, codes, &defaults).unwrap();
        assert!(settings.reordering().is_none());
        settings.set_reordering(&groups, &[-1], &defaults).unwrap();
        assert_eq!(settings, defaults);
    }
    // Hiragana and Katakana share the actual ICU77 range; both duplicate and
    // equivalent script requests fail before replacing existing settings.
    for codes in [&[25, 25][..], &[20, 22][..], &[103, 103][..], &[-1, 25][..]] {
        assert!(matches!(
            settings.set_reordering(&groups, codes, &defaults),
            Err(Error::InvalidSettings(_))
        ));
        assert_eq!(settings, defaults);
    }
}
