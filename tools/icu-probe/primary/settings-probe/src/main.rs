//! Independent CLI adapter for the prototype's public settings and key APIs.
//! No native API, reference output, locale-to-key mapping, or normalization.

use icu77_root_primary::{
    Collator77, Data77, Error, NfdData77, ScriptGroups77, Settings77, Strength,
};
use std::error::Error as StdError;
use std::fmt::Write as _;
use std::fs;
use std::io::{self, BufRead, Write};
use std::process::ExitCode;
use std::sync::Arc;

fn codes(text: &str) -> Result<Vec<i32>, Box<dyn StdError>> {
    if text.is_empty() {
        return Ok(Vec::new());
    }
    text.split(',')
        .map(|value| value.parse::<i32>().map_err(Into::into))
        .collect()
}

fn reorder_codes(settings: &Settings77) -> String {
    settings
        .reordering()
        .map_or_else(String::new, |reordering| {
            reordering
                .codes()
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>()
                .join(",")
        })
}

fn key(collator: &mut Collator77, input: &[u16], strength: Strength) -> Result<String, Error> {
    collator.settings_mut().set_strength(strength);
    let value = collator.sort_key_utf16(input, false)?;
    let mut result = String::with_capacity(value.raw_icu.len() * 2);
    for byte in value.raw_icu {
        write!(result, "{byte:02x}").expect("formatting to a String cannot fail");
    }
    Ok(result)
}

fn boost_key(
    collator: &mut Collator77,
    input: &[u16],
    strength: Strength,
) -> Result<String, Error> {
    collator.settings_mut().set_strength(strength);
    let value = collator.sort_key_utf16(input, false)?;
    let mut result = String::new();
    for weight in value.boost {
        if !result.is_empty() {
            result.push(',');
        }
        write!(result, "{weight:08x}").expect("formatting to a String cannot fail");
    }
    Ok(result)
}

fn run() -> Result<(), Box<dyn StdError>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let boost_fields = args.len() == 7 && args[6] == "--boost-fields";
    if args.len() != 6 && !boost_fields {
        return Err(
            "usage: icu77-settings-probe ROOT NFD SCRIPTS INITIAL_SETTINGS DEFAULT_SETTINGS OWNER_OR_DASH [--boost-fields]".into(),
        );
    }
    let root = Arc::new(Data77::from_bytes(&fs::read(&args[0])?)?);
    let data = if args[5] == "-" {
        root
    } else {
        Arc::new(Data77::from_owner_bytes(&fs::read(&args[5])?, root)?)
    };
    let nfd = Arc::new(NfdData77::from_bytes(&fs::read(&args[1])?)?);
    let groups = ScriptGroups77::from_bytes(&fs::read(&args[2])?)?;
    let initial = Settings77::from_bytes(&fs::read(&args[3])?)?;
    let defaults = Settings77::from_bytes(&fs::read(&args[4])?)?;
    let stdin = io::stdin();
    let mut input = stdin.lock().lines();
    if input.next().transpose()?.as_deref() != Some("case_id\tsetup_codes\trequest_codes\tu16_hex")
    {
        return Err("invalid settings probe input header".into());
    }
    let stdout = io::stdout();
    let mut output = io::BufWriter::new(stdout.lock());
    write!(
        output,
        "case_id\tstatus\timplementation_error\tbefore_codes\tafter_codes\tbefore_primary\tbefore_identical\tprimary\tsecondary\ttertiary\tquaternary\tidentical"
    )?;
    if boost_fields {
        write!(output, "\tboost_primary\tboost_identical")?;
    }
    writeln!(output)?;
    for line in input {
        let line = line?;
        let fields: Vec<_> = line.split('\t').collect();
        if fields.len() != 4 || fields[0].is_empty() {
            return Err("settings input requires exactly four TSV fields".into());
        }
        let units: Vec<u16> = if fields[3].is_empty() {
            Vec::new()
        } else {
            fields[3]
                .split(',')
                .map(|value| u16::from_str_radix(value, 16))
                .collect::<Result<_, _>>()?
        };
        let mut collator = Collator77::new(Arc::clone(&data), Arc::clone(&nfd), initial.clone());
        if fields[1] != "~" {
            collator
                .settings_mut()
                .set_reordering(&groups, &codes(fields[1])?, &defaults)?;
        }
        let before_codes = reorder_codes(collator.settings());
        let before_primary = key(&mut collator, &units, Strength::Primary)?;
        let before_identical = key(&mut collator, &units, Strength::Identical)?;
        let outcome = if fields[2] == "~" {
            Ok(())
        } else {
            collator
                .settings_mut()
                .set_reordering(&groups, &codes(fields[2])?, &defaults)
        };
        let (status, original_error) = match outcome {
            Ok(()) => ("U_ZERO_ERROR", String::new()),
            Err(error) => {
                // This explicit comparison label preserves the original Rust
                // cause in a separate field. Overflow must remain distinct from
                // illegal lists; any other prototype error fails the oracle gate.
                let status = match &error {
                    Error::InvalidSettings("script reordering exceeds primary range") => {
                        "U_BUFFER_OVERFLOW_ERROR"
                    }
                    Error::InvalidSettings("invalid others/default reorder code")
                    | Error::InvalidSettings("duplicate or equivalent reorder code")
                    | Error::InvalidSettings("default reorder code must stand alone") => {
                        "U_ILLEGAL_ARGUMENT_ERROR"
                    }
                    _ => "RUST_UNCLASSIFIED_ERROR",
                };
                (status, error.to_string())
            }
        };
        let after_codes = reorder_codes(collator.settings());
        write!(
            output,
            "{}\t{status}\t{original_error}\t{before_codes}\t{after_codes}\t{before_primary}\t{before_identical}",
            fields[0]
        )?;
        for strength in [
            Strength::Primary,
            Strength::Secondary,
            Strength::Tertiary,
            Strength::Quaternary,
            Strength::Identical,
        ] {
            write!(output, "\t{}", key(&mut collator, &units, strength)?)?;
        }
        if boost_fields {
            for strength in [Strength::Primary, Strength::Identical] {
                write!(output, "\t{}", boost_key(&mut collator, &units, strength)?)?;
            }
        }
        writeln!(output)?;
    }
    output.flush()?;
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("icu77-settings-probe: {error}");
            ExitCode::from(2)
        }
    }
}
