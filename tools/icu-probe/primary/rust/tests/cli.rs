use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn embedded_tables_run_without_reference_environment_and_rows_survive_input_errors() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_icu77-root-primary"))
        .args(["--input-format", "u32"])
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(
            b"case_id\tu32_hex\nempty\t\ninvalid\t0000d800\nafter\t00000061,00000000,00000062\n",
        )
        .unwrap();
    let result = child.wait_with_output().unwrap();
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "case_id\traw_icu_hex\tboost_u32_hex\nempty\t00\t00000000\ninvalid\tERROR:INVALID_UTF32\tERROR:INVALID_UTF32\nafter\t2b,2d,00\t0000002b,0000002d\n"
    );
    assert!(
        String::from_utf8(result.stderr)
            .unwrap()
            .contains("INVALID_UTF32")
    );
}

#[test]
fn signed_hex_fields_are_rejected_and_next_valid_row_is_processed() {
    for (format, invalid, valid, code) in [
        ("utf8", "+0", "61", "INVALID_UTF8_HEX"),
        ("u16", "+061", "0061", "INVALID_UTF16_HEX"),
        ("u32", "+0000061", "00000061", "INVALID_UTF32_HEX"),
    ] {
        let mut child = Command::new(env!("CARGO_BIN_EXE_icu77-root-primary"))
            .args(["--input-format", format])
            .env_clear()
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        let input = format!("case_id\t{format}_hex\ninvalid\t{invalid}\nafter\t{valid}\n");
        child
            .stdin
            .take()
            .unwrap()
            .write_all(input.as_bytes())
            .unwrap();
        let result = child.wait_with_output().unwrap();
        assert!(result.status.success(), "{format}");
        assert_eq!(
            String::from_utf8(result.stdout).unwrap(),
            format!(
                "case_id\traw_icu_hex\tboost_u32_hex\ninvalid\tERROR:{code}\tERROR:{code}\nafter\t2b,00\t0000002b\n"
            ),
            "{format}"
        );
        assert!(
            String::from_utf8(result.stderr).unwrap().contains(code),
            "{format}"
        );
    }
}

#[test]
fn identical_uses_embedded_nfd_data_and_preserves_row_errors() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_icu77-root-primary"))
        .args(["--strength", "identical", "--trace"])
        .env_clear()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(b"case_id\tutf8_hex\nempty\t\ninvalid\t+0\naccent\tc3a9\n")
        .unwrap();
    let result = child.wait_with_output().unwrap();
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "case_id\traw_icu_hex\tboost_u32_hex\nempty\t01,01,01,01,00\t00000001,00000001,00000001,00000001\ninvalid\tERROR:INVALID_UTF8_HEX\tERROR:INVALID_UTF8_HEX\naccent\t33,01,45,88,01,06,01,01,96,d4,ba,00\t00000033,00000001,00000045,00000088,00000001,00000006,00000001,00000001,00000096,000000d4,000000ba\n"
    );
    let diagnostics = String::from_utf8(result.stderr).unwrap();
    assert!(diagnostics.contains("\"strength\":\"identical\""));
    assert!(diagnostics.contains("\"nfd_u32_hex\":\"00000065,00000301\""));
    assert!(diagnostics.contains("INVALID_UTF8_HEX"));
}
