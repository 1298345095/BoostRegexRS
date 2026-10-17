use icu_casemap::CaseMapper;
use icu_collator::{
    Collator,
    options::{CollatorOptions, Strength},
};
use icu_locale_core::Locale;
use icu_properties::{
    CodePointMapData, CodePointSetData,
    props::{GeneralCategory, WhiteSpace},
};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    env,
    error::Error,
    fs,
    io::{BufWriter, Write},
    path::Path,
};

const FIELDS: [&str; 9] = [
    "lower", "upper", "fold", "category", "blank", "space", "digit10", "digit16", "digit36",
];
const LOCALES: [(&str, &str); 10] = [
    ("root", "und"),
    ("en_US", "en-US"),
    ("tr_TR", "tr-TR"),
    ("de_DE", "de-DE"),
    ("sv_SE", "sv-SE"),
    ("fr_CA", "fr-CA"),
    ("es_ES@collation=traditional", "es-ES-u-co-trad"),
    ("zh_CN", "zh-CN"),
    ("ja_JP", "ja-JP"),
    ("th_TH", "th-TH"),
];

#[derive(Default)]
struct Stats {
    compared: u64,
    mismatches: u64,
    unsupported: u64,
    examples: Vec<Value>,
}
impl Stats {
    fn record(&mut self, cp: u32, actual: Option<u32>, expected: u32) {
        if let Some(actual) = actual {
            self.compared += 1;
            if actual != expected {
                self.mismatches += 1;
                if self.examples.len() < 8 {
                    self.examples.push(json!({"codepoint": format!("U+{cp:04X}"), "actual": actual, "expected": expected}));
                }
            }
        } else {
            self.unsupported += 1;
        }
    }
    fn json(&self) -> Value {
        json!({"compared": self.compared, "mismatches": self.mismatches, "unsupported": self.unsupported, "first_examples": self.examples})
    }
}

fn digit(cp: u32, radix: u32, decimal: Option<u32>) -> u32 {
    let value = decimal.or_else(|| match cp {
        0x41..=0x5a => Some(cp - 0x41 + 10),
        0x61..=0x7a => Some(cp - 0x61 + 10),
        0xff21..=0xff3a => Some(cp - 0xff21 + 10),
        0xff41..=0xff5a => Some(cp - 0xff41 + 10),
        _ => None,
    });
    value.filter(|&n| n < radix).unwrap_or(u32::MAX)
}

fn codepoints(reference: &Path) -> Result<Value, Box<dyn Error>> {
    let data = fs::read(reference)?;
    if data.len() != 0x0011_0000 * 40 {
        return Err("expected 0x0011_0000 records of 40 bytes".into());
    }
    let case = CaseMapper::new();
    let categories = CodePointMapData::<GeneralCategory>::new();
    let white_space = CodePointSetData::new::<WhiteSpace>();
    let decimal_ranges: Vec<_> = categories
        .iter_ranges_for_value(GeneralCategory::DecimalNumber)
        .collect();
    for range in &decimal_ranges {
        if (range.end() - range.start() + 1) % 10 != 0 {
            return Err("Nd range cannot use validated ten-digit sequence adapter".into());
        }
    }
    let mut raw: BTreeMap<_, Stats> = FIELDS.map(|f| (f, Stats::default())).into();
    let mut adapted: BTreeMap<_, Stats> = FIELDS.map(|f| (f, Stats::default())).into();
    for (index, record) in data.as_chunks::<40>().0.iter().enumerate() {
        let words: Vec<_> = record
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| u32::from_le_bytes(*b))
            .collect();
        let cp = u32::try_from(index)?;
        if words[0] != cp {
            return Err(format!("nonsequential reference at {cp:X}").into());
        }
        let scalar = char::from_u32(cp);
        let gc = categories.get32(cp);
        let raw_values = [
            scalar.map(|c| case.simple_lowercase(c) as u32),
            scalar.map(|c| case.simple_uppercase(c) as u32),
            scalar.map(|c| case.simple_fold(c) as u32),
            Some(gc as u32),
            None,
            Some(u32::from(white_space.contains32(cp))),
            None,
            None,
            None,
        ];
        // ICU's u_isspace includes the four information separators U+001C..001F.
        let blank = cp == 9 || gc == GeneralCategory::SpaceSeparator;
        let space = white_space.contains32(cp) || (0x1c..=0x1f).contains(&cp);
        let decimal = decimal_ranges
            .iter()
            .find(|r| r.contains(&cp))
            .map(|r| (cp - r.start()) % 10);
        let adapter_values = [
            Some(raw_values[0].unwrap_or(cp)),
            Some(raw_values[1].unwrap_or(cp)),
            Some(raw_values[2].unwrap_or(cp)),
            Some(gc as u32),
            Some(u32::from(blank)),
            Some(u32::from(space)),
            Some(digit(cp, 10, decimal)),
            Some(digit(cp, 16, decimal)),
            Some(digit(cp, 36, decimal)),
        ];
        for (i, field) in FIELDS.iter().enumerate() {
            raw.get_mut(field)
                .expect("known field")
                .record(cp, raw_values[i], words[i + 1]);
            adapted.get_mut(field).expect("known field").record(
                cp,
                adapter_values[i],
                words[i + 1],
            );
        }
    }
    Ok(json!({
        "reference": reference.display().to_string(), "records": 0x0011_0000, "record_bytes": 40,
        "raw_icu4x": raw.iter().map(|(k,v)| (*k,v.json())).collect::<BTreeMap<_,_>>(),
        "icu_compat_adapter": adapted.iter().map(|(k,v)| (*k,v.json())).collect::<BTreeMap<_,_>>(),
        "surrogate_policy": {"raw_simple_case": "unsupported: Rust char rejects U+D800..DFFF", "adapter_simple_case": "identity for surrogate codepoints, Unicode simple case mapping default"},
        "raw_missing_apis": ["POSIX blank function", "ICU u_digit numeric conversion"],
        "sort_key_output": "unsupported: ICU4X 2.0 has no public sort-key API",
        "data_versions": {"icu4x": "2.0.0", "unicode": "16.0.0", "cldr": "47"},
    }))
}

fn ordering(cases_path: &Path, output: &Path) -> Result<Value, Box<dyn Error>> {
    let contents = fs::read_to_string(cases_path)?;
    let mut cases = Vec::new();
    for line in contents.lines() {
        if line.is_empty() || line == "case_id\tutf8_hex" {
            continue;
        }
        let (id, hex) = line.split_once('\t').ok_or("invalid case row")?;
        if hex.len() % 2 != 0 {
            return Err("odd UTF-8 hex length".into());
        }
        let bytes = (0..hex.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&hex[i..i + 2], 16))
            .collect::<Result<Vec<_>, _>>()?;
        cases.push((id.to_owned(), String::from_utf8(bytes)?));
    }
    let mut writer = BufWriter::new(fs::File::create(output)?);
    writeln!(writer, "locale\tstrength\tleft_id\tright_id\tordering")?;
    let mut count = 0;
    let mut failures = Vec::new();
    for (icu_id, bcp47) in LOCALES {
        let locale: Locale = bcp47.parse()?;
        for (label, strength) in [
            ("primary", Strength::Primary),
            ("identical", Strength::Identical),
        ] {
            let mut options = CollatorOptions::default();
            options.strength = Some(strength);
            let result = Collator::try_new(locale.clone().into(), options);
            if let Err(error) = &result {
                failures
                    .push(json!({"locale": icu_id, "strength": label, "error": error.to_string()}));
            }
            for (i, (left_id, left)) in cases.iter().enumerate() {
                for (right_id, right) in &cases[i + 1..] {
                    let sign = match &result {
                        Ok(collator) => match collator.compare(left, right) {
                            std::cmp::Ordering::Less => "-1",
                            std::cmp::Ordering::Equal => "0",
                            std::cmp::Ordering::Greater => "1",
                        },
                        Err(_) => "unsupported",
                    };
                    writeln!(writer, "{icu_id}\t{label}\t{left_id}\t{right_id}\t{sign}")?;
                    count += 1;
                }
            }
        }
    }
    writer.flush()?;
    Ok(
        json!({"cases": cases.len(), "rows": count, "construction_failures": failures, "locale_mappings": LOCALES.iter().map(|(a,b)|json!({"icu":a,"bcp47":b})).collect::<Vec<_>>(), "fallback_policy": "explicit mapping; constructor error produces unsupported; ICU4X internal locale data fallback remains library behavior, pairwise agreement alone does not prove locale identity"}),
    )
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = env::args().skip(1).collect();
    let arg = |name| {
        args.windows(2)
            .find(|w| w[0] == name)
            .map(|w| w[1].as_str())
    };
    let reference = arg("--reference").ok_or("--reference PATH required")?;
    let output = arg("--summary").ok_or("--summary PATH required")?;
    let mut summary = codepoints(Path::new(reference))?;
    if let Some(cases) = arg("--cases") {
        let order_output =
            arg("--ordering-output").ok_or("--ordering-output PATH required with --cases")?;
        summary["collation_comparison"] = ordering(Path::new(cases), Path::new(order_output))?;
    }
    fs::write(
        output,
        format!("{}\n", serde_json::to_string_pretty(&summary)?),
    )?;
    println!("Wrote {output}");
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
