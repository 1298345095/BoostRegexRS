use std::env;
use std::fmt::Write as _;
use std::fs;
use std::io::{self, BufRead, Write};
use std::process::ExitCode;

use icu77_root_primary::{Data77, Key, RootPrimary};

const EMBEDDED_DATA: &[u8] = include_bytes!("../../data/root-icu77.bin");

#[derive(Clone, Copy)]
enum InputFormat {
    Utf8,
    U32,
    U16,
}

impl InputFormat {
    fn name(self) -> &'static str {
        match self {
            Self::Utf8 => "utf8",
            Self::U32 => "u32",
            Self::U16 => "u16",
        }
    }
}

struct Options {
    data: Option<String>,
    format: InputFormat,
    trace: bool,
    icu_utf16_only: bool,
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("icu77-root-primary: {error}");
            ExitCode::from(2)
        }
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut options = Options {
        data: None,
        format: InputFormat::Utf8,
        trace: false,
        icu_utf16_only: false,
    };
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--data" => options.data = Some(args.next().ok_or("--data needs a path")?),
            "--input-format" => {
                options.format = match args.next().as_deref() {
                    Some("utf8") => InputFormat::Utf8,
                    Some("u32") => InputFormat::U32,
                    Some("u16") => InputFormat::U16,
                    _ => return Err("--input-format must be utf8, u32, or u16".into()),
                };
            }
            "--trace" => options.trace = true,
            "--icu-utf16-only" => options.icu_utf16_only = true,
            "--help" | "-h" => {
                println!(
                    "icu77-root-primary [--data PATH] [--input-format utf8|u32|u16] [--trace] [--icu-utf16-only]\n\
                    Reads TSV from stdin: case_id<TAB>utf8_hex (or comma-separated u32/u16 hex).\n\
                    Writes: case_id<TAB>raw_icu_hex<TAB>boost_u32_hex.\n\
                    --trace writes one JSON diagnostic per input to stderr.\n\
                    --icu-utf16-only requires u16 and names the separate raw ICU diagnostic domain."
                );
                return Ok(());
            }
            _ => return Err(format!("unknown argument: {arg}").into()),
        }
    }
    if options.icu_utf16_only && !matches!(options.format, InputFormat::U16) {
        return Err("--icu-utf16-only requires --input-format u16".into());
    }
    let external_data = options.data.as_ref().map(fs::read).transpose()?;
    let collator = RootPrimary::new(Data77::from_bytes(
        external_data.as_deref().unwrap_or(EMBEDDED_DATA),
    )?);
    let stdin = io::stdin();
    let stdout = io::stdout();
    let stderr = io::stderr();
    let mut output = io::BufWriter::new(stdout.lock());
    let mut diagnostics = io::BufWriter::new(stderr.lock());
    writeln!(output, "case_id\traw_icu_hex\tboost_u32_hex")?;
    for (line_number, line) in stdin.lock().lines().enumerate() {
        let line = line?;
        let line = line.strip_suffix('\r').unwrap_or(&line);
        let (case_id, input_hex) = line
            .split_once('\t')
            .ok_or_else(|| format!("line {} is not a two-column TSV row", line_number + 1))?;
        if line_number == 0 && case_id == "case_id" {
            let expected = format!("{}_hex", options.format.name());
            if input_hex != expected {
                return Err(format!("expected TSV header case_id<TAB>{expected}").into());
            }
            continue;
        }
        if case_id.is_empty() || input_hex.contains('\t') {
            return Err(format!("line {} is not a valid two-column case", line_number + 1).into());
        }
        match compute_row(&collator, input_hex, &options) {
            Ok(key) => {
                let raw = bytes_hex(&key.raw_icu);
                let boost = u32_hex(&key.boost);
                writeln!(output, "{case_id}\t{raw}\t{boost}")?;
                if options.trace {
                    write_trace(&mut diagnostics, case_id, &options, &key, &raw, &boost)?;
                }
            }
            Err((code, description)) => {
                writeln!(output, "{case_id}\tERROR:{code}\tERROR:{code}")?;
                writeln!(diagnostics, "{}", error_json(case_id, code, &description))?;
            }
        }
    }
    output.flush()?;
    diagnostics.flush()?;
    Ok(())
}

type RowResult = Result<Key, (&'static str, String)>;

fn compute_row(collator: &RootPrimary, input: &str, options: &Options) -> RowResult {
    let result = match options.format {
        InputFormat::Utf8 => {
            let bytes =
                parse_bytes(input).map_err(|description| ("INVALID_UTF8_HEX", description))?;
            let text =
                std::str::from_utf8(&bytes).map_err(|error| ("INVALID_UTF8", error.to_string()))?;
            collator.primary_utf8(text, options.trace)
        }
        InputFormat::U32 => {
            let units =
                parse_units(input, 8).map_err(|description| ("INVALID_UTF32_HEX", description))?;
            collator.primary_u32(&units, options.trace)
        }
        InputFormat::U16 => {
            let units =
                parse_units(input, 4).map_err(|description| ("INVALID_UTF16_HEX", description))?;
            let units = units
                .into_iter()
                .map(|unit| unit as u16)
                .collect::<Vec<_>>();
            if options.icu_utf16_only {
                collator.primary_icu_utf16(&units, options.trace)
            } else {
                collator.primary_utf16(&units, options.trace)
            }
        }
    };
    result.map_err(|error| (error.code(), error.to_string()))
}

fn parse_bytes(input: &str) -> Result<Vec<u8>, String> {
    if !input.as_bytes().iter().all(u8::is_ascii_hexdigit) || !input.len().is_multiple_of(2) {
        return Err("UTF-8 hex must consist of complete byte pairs".into());
    }
    input
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| {
            u8::from_str_radix(std::str::from_utf8(pair).expect("ASCII"), 16)
                .map_err(|_| "invalid UTF-8 hexadecimal byte".into())
        })
        .collect()
}

fn parse_units(input: &str, width: usize) -> Result<Vec<u32>, String> {
    if input.is_empty() {
        return Ok(Vec::new());
    }
    input
        .split(',')
        .map(|unit| {
            if unit.len() != width || !unit.as_bytes().iter().all(u8::is_ascii_hexdigit) {
                return Err(format!(
                    "expected exactly {width} hexadecimal digits per input unit"
                ));
            }
            u32::from_str_radix(unit, 16).map_err(|_| "invalid hexadecimal input unit".into())
        })
        .collect()
}

fn bytes_hex(bytes: &[u8]) -> String {
    let mut result = String::with_capacity(bytes.len() * 3);
    for (index, byte) in bytes.iter().enumerate() {
        if index != 0 {
            result.push(',');
        }
        write!(&mut result, "{byte:02x}").expect("String writing");
    }
    result
}

fn u32_hex(values: &[u32]) -> String {
    let mut result = String::new();
    for (index, value) in values.iter().enumerate() {
        if index != 0 {
            result.push(',');
        }
        write!(&mut result, "{value:08x}").expect("String writing");
    }
    result
}

fn json_string(value: &str) -> String {
    let mut result = String::from("\"");
    for c in value.chars() {
        match c {
            '"' => result.push_str("\\\""),
            '\\' => result.push_str("\\\\"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '\t' => result.push_str("\\t"),
            c if c < ' ' => write!(&mut result, "\\u{:04x}", u32::from(c)).expect("String writing"),
            c => result.push(c),
        }
    }
    result.push('"');
    result
}

fn error_json(case_id: &str, code: &str, description: &str) -> String {
    format!(
        "{{\"case_id\":{},\"error\":{},\"detail\":{}}}",
        json_string(case_id),
        json_string(code),
        json_string(description)
    )
}

fn write_trace(
    output: &mut impl Write,
    case_id: &str,
    options: &Options,
    key: &Key,
    raw: &str,
    boost: &str,
) -> io::Result<()> {
    write!(
        output,
        "{{\"case_id\":{},\"input_format\":\"{}\",\"icu_utf16_only\":{},\"raw_icu_hex\":\"{}\",\"boost_u32_hex\":\"{}\",\"ces\":[",
        json_string(case_id),
        options.format.name(),
        options.icu_utf16_only,
        raw,
        boost
    )?;
    for (index, ce) in key.ces.as_deref().unwrap_or_default().iter().enumerate() {
        if index != 0 {
            write!(output, ",")?;
        }
        write!(output, "\"{ce:016x}\"")?;
    }
    write!(output, "],\"events\":[")?;
    for (index, event) in key.trace.as_deref().unwrap_or_default().iter().enumerate() {
        if index != 0 {
            write!(output, ",")?;
        }
        let cp = event
            .code_point
            .map_or_else(|| "null".into(), |cp| format!("\"{cp:06x}\""));
        let ce = event
            .ce
            .map_or_else(|| "null".into(), |ce| format!("\"{ce:016x}\""));
        write!(
            output,
            "{{\"input_position_cp\":{},\"code_point\":{},\"ce32\":\"{:08x}\",\"stage\":\"{}\",\"ce\":{}}}",
            event.input_position_cp, cp, event.ce32, event.kind, ce
        )?;
    }
    writeln!(output, "]}}")
}
