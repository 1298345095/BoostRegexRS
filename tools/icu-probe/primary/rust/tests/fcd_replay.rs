//! Complete native key and CE64 fixtures are test data, never runtime lookup.

use std::collections::BTreeMap;
use std::fmt::Debug;
use std::sync::Arc;

use icu77_root_primary::{Collator77, Data77, NfdData77, Settings77, Strength};

fn hex_values<T: TryFrom<u64>>(text: &str) -> Vec<T>
where
    T::Error: Debug,
{
    text.split(',')
        .filter(|field| !field.is_empty())
        .map(|field| T::try_from(u64::from_str_radix(field, 16).unwrap()).unwrap())
        .collect()
}

#[test]
fn native_full_keys_and_ces_match_with_fcd_on_and_off() {
    let root = Arc::new(Data77::from_bytes(include_bytes!("../../data/root-icu77.bin")).unwrap());
    let nfd =
        Arc::new(NfdData77::from_bytes(include_bytes!("../../data/root-icu77-nfd.bin")).unwrap());
    let faroese = Arc::new(
        Data77::from_owner_bytes(
            include_bytes!("../../data/locales/owner-0043.bin"),
            Arc::clone(&root),
        )
        .unwrap(),
    );
    let root_settings = Settings77::from_icu(0x2010, 0x0bff_ffff, None).unwrap();
    let faroese_settings =
        Settings77::from_bytes(include_bytes!("../../data/locales/settings-0001.bin")).unwrap();
    let mut collators = BTreeMap::new();
    for (profile, data, settings, normalization) in [
        ("root-off", &root, &root_settings, false),
        ("root-on", &root, &root_settings, true),
        ("fo-off", &faroese, &faroese_settings, false),
        ("fo-on", &faroese, &faroese_settings, true),
    ] {
        for (name, strength) in [
            ("primary", Strength::Primary),
            ("identical", Strength::Identical),
        ] {
            let mut settings = settings.clone();
            settings.set_normalization(normalization);
            settings.set_strength(strength);
            collators.insert(
                (profile, name),
                Collator77::new(Arc::clone(data), Arc::clone(&nfd), settings),
            );
        }
    }
    let input_count = include_str!("data/fcd77/inputs-u16.tsv")
        .lines()
        .skip(1)
        .count();
    assert_eq!(
        input_count, 1436,
        "the complete source-defined fixture corpus is required"
    );
    let mut rows = include_str!("data/fcd77/native-keys-ces.tsv").lines();
    assert_eq!(
        rows.next(),
        Some("profile\tstrength\tcase_id\tu16_hex\traw_icu_hex\tboost_u32_hex\tces64_hex")
    );
    let mut groups = BTreeMap::new();
    let mut ordinary = 0;
    let mut approved_empty = 0;
    for row in rows {
        let fields = row.split('\t').collect::<Vec<_>>();
        assert_eq!(fields.len(), 7, "malformed native key fixture row");
        let (profile, strength, id) = (fields[0], fields[1], fields[2]);
        let collator = collators
            .get(&(profile, strength))
            .expect("unknown native profile");
        let units = hex_values::<u16>(fields[3]);
        let actual = collator
            .sort_key_utf16(&units, true)
            .unwrap_or_else(|error| panic!("{profile}/{strength}/{id}: {error}"));
        assert_eq!(
            actual.raw_icu,
            hex_values::<u8>(fields[4]),
            "{profile}/{strength}/{id}: raw ICU"
        );
        assert_eq!(
            actual.boost,
            hex_values::<u32>(fields[5]),
            "{profile}/{strength}/{id}: Boost u32"
        );
        assert_eq!(
            actual.ces.as_deref(),
            Some(hex_values::<u64>(fields[6]).as_slice()),
            "{profile}/{strength}/{id}: CE64"
        );
        if profile == "fo-on" && matches!(id, "fcd/context-2-7-3" | "fcd/context-2-7-4") {
            let trace = actual.trace.as_ref().unwrap();
            assert!(
                trace.iter().any(|event| event.kind == "prefix"),
                "{id}: missing prefix coverage"
            );
            assert!(
                trace
                    .iter()
                    .any(|event| event.kind == "discontiguous_match"),
                "{id}: missing contraction replay coverage"
            );
        }
        *groups.entry((profile, strength)).or_insert(0) += 1;
        if units.is_empty() && strength == "identical" {
            approved_empty += 1;
        } else {
            ordinary += 1;
        }
    }
    assert_eq!(groups.len(), 8);
    assert!(groups.values().all(|&count| count == input_count));
    assert_eq!(approved_empty, 4);
    assert_eq!(ordinary, input_count * 8 - approved_empty);
}
