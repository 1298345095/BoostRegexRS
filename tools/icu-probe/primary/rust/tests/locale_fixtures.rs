//! Independent native keys selected from the complete passed configuration run.

use icu77_root_primary::{Collator77, Data77, NfdData77, Settings77, Strength};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Arc;

struct Fixture {
    id: &'static str,
    utf8_hex: &'static str,
    raw_icu_hex: &'static str,
    boost_u32_hex: &'static str,
}

fn fixtures() -> BTreeMap<(u16, u16, &'static str), Vec<Fixture>> {
    let mut rows = include_str!("data/locales-v2.tsv").lines();
    assert_eq!(
        rows.next(),
        Some("fixture_id\towner\tsettings\tstrength\tutf8_hex\traw_icu_hex\tboost_u32_hex")
    );
    let mut groups = BTreeMap::<_, Vec<_>>::new();
    let mut count = 0;
    for row in rows {
        let fields: [&str; 7] = row.split('\t').collect::<Vec<_>>().try_into().unwrap();
        let key = (
            fields[1].parse().unwrap(),
            fields[2].parse().unwrap(),
            fields[3],
        );
        groups.entry(key).or_default().push(Fixture {
            id: fields[0],
            utf8_hex: fields[4],
            raw_icu_hex: fields[5],
            boost_u32_hex: fields[6],
        });
        count += 1;
    }
    assert_eq!(count, 938);
    assert_eq!(groups.len(), 244);
    groups
}

fn data_directory() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../data")
}

#[test]
fn complete_native_locale_fixtures_match_the_public_collator() {
    let directory = data_directory();
    let root = Arc::new(
        Data77::from_bytes(&std::fs::read(directory.join("root-icu77.bin")).unwrap()).unwrap(),
    );
    let nfd = Arc::new(
        NfdData77::from_bytes(&std::fs::read(directory.join("root-icu77-nfd.bin")).unwrap())
            .unwrap(),
    );
    for ((owner, setting, strength), rows) in fixtures() {
        let data = if owner == 0 {
            Arc::clone(&root)
        } else {
            let bytes =
                std::fs::read(directory.join(format!("locales/owner-{owner:04}.bin"))).unwrap();
            Arc::new(Data77::from_owner_bytes(&bytes, Arc::clone(&root)).unwrap())
        };
        let bytes =
            std::fs::read(directory.join(format!("locales/settings-{setting:04}.bin"))).unwrap();
        let mut settings = Settings77::from_bytes(&bytes).unwrap();
        settings.set_strength(match strength {
            "primary" => Strength::Primary,
            "identical" => Strength::Identical,
            other => panic!("Unexpected native fixture strength: {other}"),
        });
        let collator = Collator77::new(data, Arc::clone(&nfd), settings);
        for row in rows {
            let (pairs, remainder) = row.utf8_hex.as_bytes().as_chunks::<2>();
            assert!(remainder.is_empty(), "{} input", row.id);
            let input = pairs
                .iter()
                .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
                .collect::<Vec<_>>();
            let expected_raw = row
                .raw_icu_hex
                .split(',')
                .map(|value| u8::from_str_radix(value, 16).unwrap())
                .collect::<Vec<_>>();
            let expected_boost = row
                .boost_u32_hex
                .split(',')
                .map(|value| u32::from_str_radix(value, 16).unwrap())
                .collect::<Vec<_>>();
            let key = collator
                .sort_key_utf8(std::str::from_utf8(&input).unwrap(), false)
                .unwrap();
            assert_eq!(key.raw_icu, expected_raw, "{} complete ICU bytes", row.id);
            assert_eq!(
                key.boost, expected_boost,
                "{} complete Boost elements",
                row.id
            );
        }
    }
}

#[test]
fn native_locale_fixtures_match_the_external_owner_settings_cli() {
    let directory = data_directory();
    for ((owner, setting, strength), rows) in fixtures() {
        let mut command = Command::new(env!("CARGO_BIN_EXE_icu77-root-primary"));
        command
            .env_clear()
            .args(["--strength", strength])
            .arg("--data")
            .arg(directory.join("root-icu77.bin"))
            .arg("--nfd-data")
            .arg(directory.join("root-icu77-nfd.bin"))
            .arg("--settings")
            .arg(directory.join(format!("locales/settings-{setting:04}.bin")))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if owner != 0 {
            command
                .arg("--owner")
                .arg(directory.join(format!("locales/owner-{owner:04}.bin")));
        }
        let mut child = command.spawn().unwrap();
        let mut input = String::from("case_id\tutf8_hex\n");
        for row in &rows {
            input.push_str(&format!("{}\t{}\n", row.id, row.utf8_hex));
        }
        let mut stdin = child.stdin.take().unwrap();
        let result = std::thread::scope(|scope| {
            let writer = scope.spawn(move || stdin.write_all(input.as_bytes()));
            let result = child.wait_with_output().unwrap();
            writer.join().unwrap().unwrap();
            result
        });
        assert!(
            result.status.success(),
            "owner {owner}, settings {setting}, {strength}: {}",
            String::from_utf8_lossy(&result.stderr)
        );
        assert!(result.stderr.is_empty());
        let output = String::from_utf8(result.stdout).unwrap();
        let mut actual = output.lines();
        assert_eq!(actual.next(), Some("case_id\traw_icu_hex\tboost_u32_hex"));
        for row in rows {
            let expected = format!("{}\t{}\t{}", row.id, row.raw_icu_hex, row.boost_u32_hex);
            assert_eq!(actual.next(), Some(expected.as_str()), "{} CLI", row.id);
        }
        assert!(actual.next().is_none());
    }
}
