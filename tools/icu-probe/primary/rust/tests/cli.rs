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
