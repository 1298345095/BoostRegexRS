//! Pure Rust, fixed-data ICU77 root PRIMARY/IDENTICAL sort-key research prototype.
//!
//! This standalone crate is deliberately isolated from the repository's public
//! regex API. No native library, locale service, Unicode data from `std`, or
//! normalization service is called while computing keys.

mod bocsu77;
mod ce77;
mod data77;
mod key77;
mod nfd77;

use std::fmt;

pub use data77::Data77;
pub use key77::boost_key;
pub use nfd77::NfdData77;

pub type Result<T> = std::result::Result<T, Error>;

/// Input errors and unimplemented/corrupt data are not compatibility passes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    InvalidUtf32 { position: usize, value: u32 },
    InvalidUtf16 { position: usize, value: u16 },
    UnsupportedCe32(u32),
    Data(&'static str),
}

impl Error {
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidUtf32 { .. } => "INVALID_UTF32",
            Self::InvalidUtf16 { .. } => "INVALID_UTF16",
            Self::UnsupportedCe32(_) => "UNSUPPORTED_CE32",
            Self::Data(_) => "DATA_ERROR",
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidUtf32 { position, value } => {
                write!(f, "INVALID_UTF32 at input unit {position}: {value:08x}")
            }
            Self::InvalidUtf16 { position, value } => {
                write!(f, "INVALID_UTF16 at input unit {position}: {value:04x}")
            }
            Self::UnsupportedCe32(value) => write!(f, "UNSUPPORTED_CE32: {value:08x}"),
            Self::Data(message) => write!(f, "DATA_ERROR: {message}"),
        }
    }
}

impl std::error::Error for Error {}

/// Stage-local diagnostics. `input_position_cp` is an internal CE cursor, not a
/// regex match position or public offset promise. No trace is allocated by default.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceEvent {
    pub input_position_cp: usize,
    pub code_point: Option<u32>,
    pub ce32: u32,
    pub kind: &'static str,
    pub ce: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Key {
    /// ICU byte sequence including its final NUL byte.
    pub raw_icu: Vec<u8>,
    /// Boost's complete exposed sequence, one u32 per byte.
    pub boost: Vec<u32>,
    /// Full CE64 sequence (including sentinel) when tracing is requested.
    pub ces: Option<Vec<u64>>,
    /// NFD scalars used only by the IDENTICAL level when tracing is requested.
    pub identical_nfd: Option<Vec<u32>>,
    pub trace: Option<Vec<TraceEvent>>,
}

#[derive(Debug)]
pub struct RootPrimary {
    data: Data77,
}

impl RootPrimary {
    pub fn new(data: Data77) -> Self {
        Self { data }
    }

    pub fn data(&self) -> &Data77 {
        &self.data
    }

    /// Accept valid UTF-8, retaining NUL and original canonical ordering.
    pub fn primary_utf8(&self, input: &str, trace: bool) -> Result<Key> {
        let cps = input.chars().map(u32::from).collect::<Vec<_>>();
        self.compute(&cps, trace)
    }

    /// Match Boost's checked UTF-32-to-UTF-16 input domain.
    pub fn primary_u32(&self, input: &[u32], trace: bool) -> Result<Key> {
        validate_utf32(input)?;
        self.compute(input, trace)
    }

    /// Match the checked UTF-16-to-UTF-32-to-Boost diagnostic adapter.
    pub fn primary_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        validate_utf16(input)?;
        self.primary_icu_utf16(input, trace)
    }

    /// Raw ICU UTF-16 diagnostic only: preserve unpaired units as code points.
    /// This is intentionally separate from the checked Boost input adapter.
    pub fn primary_icu_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        self.compute(&decode_utf16_units(input), trace)
    }

    fn compute(&self, input: &[u32], trace: bool) -> Result<Key> {
        let (ces, events) = ce77::Elements::new(&self.data, input, trace).collect()?;
        let raw_icu = key77::primary_bytes(&ces, &self.data.compressible);
        let boost = boost_key(&raw_icu);
        Ok(Key {
            raw_icu,
            boost,
            ces: trace.then_some(ces),
            identical_nfd: None,
            trace: events,
        })
    }
}

/// Root collation with the fixed default settings and both Boost key strengths.
/// `RootPrimary` remains available when only the PRIMARY data is needed.
#[derive(Debug)]
pub struct RootCollator {
    primary: RootPrimary,
    nfd: NfdData77,
}

impl RootCollator {
    pub fn new(data: Data77, nfd: NfdData77) -> Result<Self> {
        if data.primary_options != 0x10 {
            return Err(Error::Data("expected root default collation options"));
        }
        Ok(Self {
            primary: RootPrimary::new(data),
            nfd,
        })
    }

    pub fn data(&self) -> &Data77 {
        self.primary.data()
    }

    pub fn primary_utf8(&self, input: &str, trace: bool) -> Result<Key> {
        self.primary.primary_utf8(input, trace)
    }

    pub fn primary_u32(&self, input: &[u32], trace: bool) -> Result<Key> {
        self.primary.primary_u32(input, trace)
    }

    pub fn primary_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        self.primary.primary_utf16(input, trace)
    }

    pub fn primary_icu_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        self.primary.primary_icu_utf16(input, trace)
    }

    /// Compute default root IDENTICAL; canonical decomposition is confined to
    /// its final level. The CE iterator receives the original input unchanged.
    pub fn identical_utf8(&self, input: &str, trace: bool) -> Result<Key> {
        self.identical(&input.chars().map(u32::from).collect::<Vec<_>>(), trace)
    }

    pub fn identical_u32(&self, input: &[u32], trace: bool) -> Result<Key> {
        validate_utf32(input)?;
        self.identical(input, trace)
    }

    pub fn identical_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        validate_utf16(input)?;
        self.identical_icu_utf16(input, trace)
    }

    /// Raw ICU UTF-16 diagnostic, distinct from Boost's checked input domain.
    pub fn identical_icu_utf16(&self, input: &[u16], trace: bool) -> Result<Key> {
        self.identical(&decode_utf16_units(input), trace)
    }

    fn identical(&self, input: &[u32], trace: bool) -> Result<Key> {
        let data = self.data();
        let (ces, events) = ce77::Elements::new(data, input, trace).collect()?;
        let nfd = self.nfd.normalize(input);
        let raw_icu = key77::identical_bytes(&ces, &data.compressible, &nfd);
        let boost = boost_key(&raw_icu);
        Ok(Key {
            raw_icu,
            boost,
            ces: trace.then_some(ces),
            identical_nfd: trace.then_some(nfd),
            trace: events,
        })
    }
}

fn validate_utf32(input: &[u32]) -> Result<()> {
    for (position, value) in input.iter().copied().enumerate() {
        if value > 0x10ffff || (0xd800..=0xdfff).contains(&value) {
            return Err(Error::InvalidUtf32 { position, value });
        }
    }
    Ok(())
}

fn validate_utf16(input: &[u16]) -> Result<()> {
    let mut position = 0;
    while position < input.len() {
        let value = input[position];
        if (0xd800..=0xdbff).contains(&value)
            && input
                .get(position + 1)
                .is_some_and(|next| (0xdc00..=0xdfff).contains(next))
        {
            position += 2;
        } else if (0xd800..=0xdfff).contains(&value) {
            return Err(Error::InvalidUtf16 { position, value });
        } else {
            position += 1;
        }
    }
    Ok(())
}

/// Decode exactly as ordinary ICU UTF16CollationIterator: pair valid surrogates,
/// and keep an unpaired unit unchanged for the explicitly raw ICU diagnostic.
fn decode_utf16_units(input: &[u16]) -> Vec<u32> {
    let mut output = Vec::with_capacity(input.len());
    let mut position = 0;
    while let Some(unit) = input.get(position).copied() {
        position += 1;
        if (0xd800..=0xdbff).contains(&unit)
            && let Some(trail) = input
                .get(position)
                .copied()
                .filter(|trail| (0xdc00..=0xdfff).contains(trail))
        {
            output.push(0x10000 + ((u32::from(unit) - 0xd800) << 10) + u32::from(trail) - 0xdc00);
            position += 1;
        } else {
            output.push(u32::from(unit));
        }
    }
    output
}
