// © 2016 and later: Unicode, Inc. and others.
// Copyright (C) 2012-2015, International Business Machines Corporation and others.
// All Rights Reserved.
// Rust adaptation of ICU77 collationsettings.{h,cpp} and collationdata.cpp.
// See ../NOTICE.md, ../LOCALE-MECHANISMS.md and ../../data/LICENSE-ICU.txt.

//! Effective settings and script reordering from fixed ICU77 data.

use crate::data77::Reader;
use crate::{Error, Result};

pub(crate) const CHECK_FCD: u32 = 1;
pub(crate) const NUMERIC: u32 = 2;
pub(crate) const ALTERNATE_MASK: u32 = 0x0c;
pub(crate) const UPPER_FIRST: u32 = 0x100;
pub(crate) const CASE_FIRST: u32 = 0x200;
pub(crate) const CASE_LEVEL: u32 = 0x400;
pub(crate) const BACKWARD_SECONDARY: u32 = 0x800;

const STRENGTH_MASK: u32 = 0xf000;
const MAX_VARIABLE_MASK: u32 = 0x70;
const REORDER_FIRST: i32 = 0x1000;
const SCRIPT_LATIN: i32 = 25;
const SCRIPT_UNKNOWN: i32 = 103;
const REORDER_DEFAULT: i32 = -1;
const SPECIAL_GROUPS: usize = 8;
const RESERVED_SCRIPT_SLOTS: [usize; 2] = [14, 15];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum Strength {
    Primary = 0,
    Secondary = 1,
    Tertiary = 2,
    Quaternary = 3,
    Identical = 15,
}

impl Strength {
    pub fn name(self) -> &'static str {
        match self {
            Self::Primary => "primary",
            Self::Secondary => "secondary",
            Self::Tertiary => "tertiary",
            Self::Quaternary => "quaternary",
            Self::Identical => "identical",
        }
    }

    fn from_options(options: u32) -> Result<Self> {
        match options >> 12 {
            0 => Ok(Self::Primary),
            1 => Ok(Self::Secondary),
            2 => Ok(Self::Tertiary),
            3 => Ok(Self::Quaternary),
            15 => Ok(Self::Identical),
            _ => Err(Error::InvalidSettings("invalid collation strength")),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CaseFirst {
    Off,
    Lower,
    Upper,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum MaxVariable {
    Space = 0,
    Punctuation = 1,
    Symbol = 2,
    Currency = 3,
}

/// Immutable primary reordering, including split lead-byte ranges.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reordering77 {
    codes: Vec<i32>,
    table: [u8; 256],
    min_high_no_reorder: u32,
    ranges: Vec<u32>,
}

impl Reordering77 {
    /// Read the actual ICU settings fields, without recomputing their order.
    pub fn from_icu(
        codes: Vec<i32>,
        table: [u8; 256],
        min_high_no_reorder: u32,
        ranges: Vec<u32>,
    ) -> Result<Self> {
        if table[..3] != [0, 1, 2]
            || table[255] != 255
            || min_high_no_reorder & 0xffff != 0
            || min_high_no_reorder > 0xff00_0000
            || (min_high_no_reorder != 0 && min_high_no_reorder < 0x0300_0000)
            || ranges.windows(2).any(|pair| pair[0] >> 16 >= pair[1] >> 16)
            || ranges
                .iter()
                .any(|pair| !(-255..=255).contains(&((*pair as i16) as i32)))
            || ranges
                .first()
                .is_some_and(|pair| pair >> 24 < 3 || pair & 0xff0000 == 0)
            || (!ranges.is_empty()
                && ranges.last().map(|pair| pair & 0xffff0000) != Some(min_high_no_reorder))
            || ranges.last().is_some_and(|pair| pair & 0xffff == 0)
            || (ranges.is_empty() && min_high_no_reorder & 0xff0000 != 0)
        {
            return Err(Error::Data("invalid primary reordering fields"));
        }
        let unused_leads = unused_primary_leads()?;
        let mut split_leads = [false; 256];
        for pair in &ranges {
            if pair & 0xff0000 != 0 {
                split_leads[(pair >> 24) as usize] = true;
            }
        }
        for lead in 3..255 {
            let byte = table[lead];
            if (split_leads[lead] && byte != 0)
                || (!split_leads[lead] && !unused_leads[lead] && !(3..255).contains(&byte))
            {
                return Err(Error::Data("unexplained or missing split primary lead"));
            }
        }
        if !table_matches_ranges(&table, min_high_no_reorder, &ranges, &unused_leads) {
            return Err(Error::Data("primary reorder table/ranges disagree"));
        }
        Ok(Self {
            codes,
            table,
            min_high_no_reorder,
            ranges,
        })
    }

    pub fn codes(&self) -> &[i32] {
        &self.codes
    }

    pub fn table(&self) -> &[u8; 256] {
        &self.table
    }

    pub fn min_high_no_reorder(&self) -> u32 {
        self.min_high_no_reorder
    }

    pub fn ranges(&self) -> &[u32] {
        &self.ranges
    }

    pub(crate) fn reorder(&self, primary: u32) -> u32 {
        let byte = self.table[(primary >> 24) as usize];
        if byte != 0 || primary <= 1 {
            (u32::from(byte) << 24) | (primary & 0xffffff)
        } else if primary >= self.min_high_no_reorder {
            primary
        } else {
            let rounded = primary | 0xffff;
            let range = self.ranges[self.ranges.partition_point(|range| rounded >= *range)];
            primary.wrapping_add(range << 24)
        }
    }
}

fn unused_primary_leads() -> Result<[bool; 256]> {
    // makeReorderRanges leaves the two reserved script intervals unallocated.
    // setReordering may wrap their unused table slots to zero. Derive these
    // intervals from fixed ICU77 script metadata, not from particular settings.
    let groups = ScriptGroups77::from_bytes(include_bytes!("../../data/locales/scripts.bin"))?;
    let mut unused = [false; 256];
    for slot in RESERVED_SCRIPT_SLOTS {
        let index = usize::from(groups.scripts_index[groups.num_scripts + slot]);
        if index != 0 {
            let first = usize::from(groups.script_starts[index]).div_ceil(256);
            let limit = usize::from(groups.script_starts[index + 1]) / 256;
            for lead in unused.iter_mut().take(limit).skip(first) {
                *lead = true;
            }
        }
    }
    Ok(unused)
}

fn table_matches_ranges(
    table: &[u8; 256],
    minimum: u32,
    ranges: &[u32],
    unused_leads: &[bool; 256],
) -> bool {
    // aliasReordering discards the minimum when there are no split ranges;
    // setReordering retains its final whole-byte limit. Preserve both forms.
    if ranges.is_empty() && minimum == 0 {
        return true;
    }
    let mut lead = (ranges.first().copied().unwrap_or(minimum) >> 24) as usize;
    let mut previous_limit = lead << 8;
    for &pair in ranges {
        let limit = (pair >> 16) as usize;
        let offset = i32::from(pair as i16);
        for (byte, &unused) in unused_leads
            .iter()
            .enumerate()
            .take((limit - 1) / 256 + 1)
            .skip(previous_limit / 256)
        {
            if !unused && !(3..255).contains(&(byte as i32 + offset)) {
                return false;
            }
        }
        previous_limit = limit;
        let limit_lead = limit / 256;
        while lead < limit_lead {
            if table[lead] != (lead as i32 + offset) as u8 {
                return false;
            }
            lead += 1;
        }
        if limit & 0xff != 0 {
            // The caller already checked that every partial limit has a zero
            // table slot. Later boundaries can share the same split lead.
            lead = limit_lead + 1;
        }
    }
    table
        .iter()
        .enumerate()
        .skip(lead)
        .all(|(lead, &byte)| byte == lead as u8)
}

/// Effective settings after tailoring defaults and caller overrides.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Settings77 {
    pub(crate) options: u32,
    pub(crate) variable_top: u32,
    reordering: Option<Reordering77>,
}

impl Settings77 {
    /// Decode the versioned BRSSET77 export, independent of a locale's tables.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let mut reader = Reader::new(bytes);
        read_header(&mut reader, b"BRSSET77")?;
        let options = reader.u32()?;
        let variable_top = reader.u32()?;
        let count = reader.count(4)?;
        let mut codes = Vec::with_capacity(count);
        for _ in 0..count {
            codes.push(reader.u32()? as i32);
        }
        let table = match reader.count(1)? {
            0 => None,
            256 => Some(reader.take(256)?.try_into().expect("checked table length")),
            _ => return Err(Error::Data("reorder table must have zero or 256 bytes")),
        };
        let min_high = reader.u32()?;
        let count = reader.count(4)?;
        let mut ranges = Vec::with_capacity(count);
        for _ in 0..count {
            ranges.push(reader.u32()?);
        }
        reader.finish()?;
        let reordering = if let Some(table) = table {
            Some(Reordering77::from_icu(codes, table, min_high, ranges)?)
        } else {
            if !codes.is_empty() || min_high != 0 || !ranges.is_empty() {
                return Err(Error::Data("reorder fields without a reorder table"));
            }
            None
        };
        Self::from_icu(options, variable_top, reordering)
    }

    pub fn from_icu(
        options: u32,
        variable_top: u32,
        reordering: Option<Reordering77>,
    ) -> Result<Self> {
        Strength::from_options(options)?;
        if options & 0x80 != 0
            || !matches!(options & ALTERNATE_MASK, 0 | 4)
            || (options & MAX_VARIABLE_MASK) >> 4 > 3
            || options & (UPPER_FIRST | CASE_FIRST) == UPPER_FIRST
            || variable_top == u32::MAX
        {
            return Err(Error::InvalidSettings("reserved ICU77 collation options"));
        }
        Ok(Self {
            options,
            variable_top,
            reordering,
        })
    }

    pub fn options(&self) -> u32 {
        self.options
    }

    pub fn variable_top(&self) -> u32 {
        self.variable_top
    }

    pub fn reordering(&self) -> Option<&Reordering77> {
        self.reordering.as_ref()
    }

    pub fn strength(&self) -> Strength {
        Strength::from_options(self.options).expect("validated settings")
    }

    pub fn set_strength(&mut self, strength: Strength) {
        self.options = (self.options & !STRENGTH_MASK) | ((strength as u32) << 12);
    }

    pub fn set_normalization(&mut self, enabled: bool) {
        self.set_flag(CHECK_FCD, enabled);
    }

    pub fn set_numeric(&mut self, enabled: bool) {
        self.set_flag(NUMERIC, enabled);
    }

    pub fn set_backward_secondary(&mut self, enabled: bool) {
        self.set_flag(BACKWARD_SECONDARY, enabled);
    }

    pub fn set_case_level(&mut self, enabled: bool) {
        self.set_flag(CASE_LEVEL, enabled);
    }

    pub fn set_case_first(&mut self, order: CaseFirst) {
        self.options &= !(CASE_FIRST | UPPER_FIRST);
        self.options |= match order {
            CaseFirst::Off => 0,
            CaseFirst::Lower => CASE_FIRST,
            CaseFirst::Upper => CASE_FIRST | UPPER_FIRST,
        };
    }

    pub fn set_shifted(&mut self, enabled: bool) {
        self.options = (self.options & !ALTERNATE_MASK) | if enabled { 4 } else { 0 };
    }

    pub fn set_max_variable(&mut self, groups: &ScriptGroups77, group: MaxVariable) -> Result<()> {
        let top = groups.last_primary(REORDER_FIRST + group as i32);
        if top == 0 {
            return Err(Error::Data("missing variable group in script data"));
        }
        self.variable_top = top;
        self.options = (self.options & !MAX_VARIABLE_MASK) | ((group as u32) << 4);
        Ok(())
    }

    /// Match ICU's numeric reorder-code API. `[-1]` restores tailoring defaults;
    /// an empty list or `[103]` disables reordering.
    pub fn set_reordering(
        &mut self,
        groups: &ScriptGroups77,
        codes: &[i32],
        defaults: &Self,
    ) -> Result<()> {
        self.reordering = if codes == [REORDER_DEFAULT] {
            defaults.reordering.clone()
        } else {
            groups.make_reordering(codes)?
        };
        Ok(())
    }

    pub(crate) fn check_fcd(&self) -> bool {
        self.options & CHECK_FCD != 0
    }

    pub(crate) fn numeric(&self) -> bool {
        self.options & NUMERIC != 0
    }

    pub(crate) fn tertiary_mask(&self) -> u32 {
        if self.options & (CASE_LEVEL | CASE_FIRST) == CASE_FIRST {
            0xff3f
        } else {
            0x3f3f
        }
    }

    pub(crate) fn reorder(&self, primary: u32) -> u32 {
        self.reordering
            .as_ref()
            .map_or(primary, |reordering| reordering.reorder(primary))
    }

    fn set_flag(&mut self, bit: u32, enabled: bool) {
        self.options = (self.options & !bit) | if enabled { bit } else { 0 };
    }
}

/// The complete script/group range mapping used to compute a new reorder list.
#[derive(Debug)]
pub struct ScriptGroups77 {
    num_scripts: usize,
    scripts_index: Vec<u16>,
    script_starts: Vec<u16>,
}

impl ScriptGroups77 {
    /// Decode the fixed script/group mapping used by arbitrary reorder lists.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let mut reader = Reader::new(bytes);
        read_header(&mut reader, b"BRSSCR77")?;
        let num_scripts = reader.u32()?;
        let count = reader.count(2)?;
        let mut index = Vec::with_capacity(count);
        for _ in 0..count {
            index.push(reader.u16()?);
        }
        let count = reader.count(2)?;
        let mut starts = Vec::with_capacity(count);
        for _ in 0..count {
            starts.push(reader.u16()?);
        }
        reader.finish()?;
        Self::from_icu(num_scripts, index, starts)
    }

    pub fn from_icu(
        num_scripts: u32,
        scripts_index: Vec<u16>,
        script_starts: Vec<u16>,
    ) -> Result<Self> {
        let num_scripts = num_scripts as usize;
        if scripts_index.len() != num_scripts + 16
            || num_scripts <= SCRIPT_LATIN as usize
            || !(3..=256).contains(&script_starts.len())
            || script_starts[..2] != [0, 0x0300]
            || script_starts.last() != Some(&0xff00)
            || script_starts.windows(2).any(|pair| pair[0] >= pair[1])
            || scripts_index
                .iter()
                .any(|index| usize::from(*index) >= script_starts.len() - 1)
            || scripts_index[SCRIPT_LATIN as usize] == 0
        {
            return Err(Error::Data("invalid ICU77 script group ranges"));
        }
        Ok(Self {
            num_scripts,
            scripts_index,
            script_starts,
        })
    }

    pub fn first_primary(&self, code: i32) -> u32 {
        let index = self.script_index(code);
        if index == 0 {
            0
        } else {
            u32::from(self.script_starts[index]) << 16
        }
    }

    pub fn last_primary(&self, code: i32) -> u32 {
        let index = self.script_index(code);
        if index == 0 {
            0
        } else {
            (u32::from(self.script_starts[index + 1]) << 16) - 1
        }
    }

    pub fn equivalent_scripts(&self, code: i32) -> Vec<i32> {
        let index = self.script_index(code);
        if index == 0 {
            Vec::new()
        } else if code >= REORDER_FIRST {
            vec![code]
        } else {
            (0..self.num_scripts)
                .filter(|script| usize::from(self.scripts_index[*script]) == index)
                .map(|script| script as i32)
                .collect()
        }
    }

    pub fn group_for_primary(&self, primary: u32) -> Option<i32> {
        let primary = primary >> 16;
        if primary < u32::from(self.script_starts[1])
            || primary >= u32::from(*self.script_starts.last().expect("validated ranges"))
        {
            return None;
        }
        let index = self
            .script_starts
            .partition_point(|start| u32::from(*start) <= primary)
            - 1;
        self.scripts_index[..self.num_scripts]
            .iter()
            .position(|candidate| usize::from(*candidate) == index)
            .map(|script| script as i32)
            .or_else(|| {
                self.scripts_index[self.num_scripts..self.num_scripts + SPECIAL_GROUPS]
                    .iter()
                    .position(|candidate| usize::from(*candidate) == index)
                    .map(|group| REORDER_FIRST + group as i32)
            })
    }

    pub fn make_reordering(&self, codes: &[i32]) -> Result<Option<Reordering77>> {
        let ranges = self.make_ranges(codes, false)?;
        if ranges.is_empty() {
            return Ok(None);
        }
        let min_high = ranges.last().expect("nonempty ranges") & 0xffff0000;
        let mut table = [0; 256];
        let mut byte = 0;
        let mut first_split = None;
        for (index, &pair) in ranges.iter().enumerate() {
            let limit = (pair >> 24) as usize;
            while byte < limit {
                table[byte] = (byte as u32).wrapping_add(pair) as u8;
                byte += 1;
            }
            if pair & 0xff0000 != 0 {
                table[limit] = 0;
                byte = limit + 1;
                first_split.get_or_insert(index);
            }
        }
        while byte < table.len() {
            table[byte] = byte as u8;
            byte += 1;
        }
        let ranges = first_split.map_or_else(Vec::new, |first| ranges[first..].to_vec());
        Reordering77::from_icu(codes.to_vec(), table, min_high, ranges).map(Some)
    }

    fn script_index(&self, code: i32) -> usize {
        if code < 0 {
            0
        } else if (code as usize) < self.num_scripts {
            usize::from(self.scripts_index[code as usize])
        } else if (REORDER_FIRST..REORDER_FIRST + SPECIAL_GROUPS as i32).contains(&code) {
            usize::from(self.scripts_index[self.num_scripts + (code - REORDER_FIRST) as usize])
        } else {
            0
        }
    }

    fn make_ranges(&self, codes: &[i32], latin_must_move: bool) -> Result<Vec<u32>> {
        if codes.is_empty() || codes == [SCRIPT_UNKNOWN] {
            return Ok(Vec::new());
        }
        let mut table = [0; 256];
        for reserved in RESERVED_SCRIPT_SLOTS {
            let index = usize::from(self.scripts_index[self.num_scripts + reserved]);
            if index != 0 {
                table[index] = 0xff;
            }
        }
        let mut low_start = i32::from(self.script_starts[1]);
        let mut high_limit = i32::from(*self.script_starts.last().expect("validated ranges"));
        let mut specials = 0_u32;
        for &code in codes {
            if (REORDER_FIRST..REORDER_FIRST + SPECIAL_GROUPS as i32).contains(&code) {
                specials |= 1 << (code - REORDER_FIRST);
            }
        }
        for group in 0..SPECIAL_GROUPS {
            let index = usize::from(self.scripts_index[self.num_scripts + group]);
            if index != 0 && specials & (1 << group) == 0 {
                low_start = self.add_low(&mut table, index, low_start);
            }
        }
        let mut skipped_reserved = 0;
        if specials == 0 && codes[0] == SCRIPT_LATIN && !latin_must_move {
            let index = usize::from(self.scripts_index[SCRIPT_LATIN as usize]);
            let start = i32::from(self.script_starts[index]);
            skipped_reserved = start - low_start;
            low_start = start;
        }
        let mut reorder_to_end = false;
        let mut length = codes.len();
        let mut position = 0;
        while position < length {
            let script = codes[position];
            position += 1;
            if script == SCRIPT_UNKNOWN {
                reorder_to_end = true;
                while position < length {
                    length -= 1;
                    let script = codes[length];
                    if script == SCRIPT_UNKNOWN || script == REORDER_DEFAULT {
                        return Err(Error::InvalidSettings(
                            "invalid others/default reorder code",
                        ));
                    }
                    let index = self.script_index(script);
                    if index == 0 {
                        continue;
                    }
                    if table[index] != 0 {
                        return Err(Error::InvalidSettings(
                            "duplicate or equivalent reorder code",
                        ));
                    }
                    high_limit = self.add_high(&mut table, index, high_limit);
                }
                break;
            }
            if script == REORDER_DEFAULT {
                return Err(Error::InvalidSettings(
                    "default reorder code must stand alone",
                ));
            }
            let index = self.script_index(script);
            if index == 0 {
                continue;
            }
            if table[index] != 0 {
                return Err(Error::InvalidSettings(
                    "duplicate or equivalent reorder code",
                ));
            }
            low_start = self.add_low(&mut table, index, low_start);
        }
        for index in 1..self.script_starts.len() - 1 {
            if table[index] != 0 {
                continue;
            }
            let start = i32::from(self.script_starts[index]);
            if !reorder_to_end && start > low_start {
                low_start = start;
            }
            low_start = self.add_low(&mut table, index, low_start);
        }
        if low_start > high_limit {
            if !latin_must_move && low_start - (skipped_reserved & 0xff00) <= high_limit {
                return self.make_ranges(codes, true);
            }
            return Err(Error::InvalidSettings(
                "script reordering exceeds primary range",
            ));
        }
        let mut ranges = Vec::new();
        let mut offset = 0;
        let mut index = 1;
        loop {
            let mut next_offset = offset;
            while index < self.script_starts.len() - 1 {
                let lead = table[index];
                if lead != 0xff {
                    next_offset = i32::from(lead) - i32::from(self.script_starts[index] >> 8);
                    if next_offset != offset {
                        break;
                    }
                }
                index += 1;
            }
            if offset != 0 || index < self.script_starts.len() - 1 {
                ranges
                    .push((u32::from(self.script_starts[index]) << 16) | (offset as u32 & 0xffff));
            }
            if index == self.script_starts.len() - 1 {
                break;
            }
            offset = next_offset;
        }
        Ok(ranges)
    }

    fn add_low(&self, table: &mut [u8; 256], index: usize, mut low: i32) -> i32 {
        let start = i32::from(self.script_starts[index]);
        if start & 0xff < low & 0xff {
            low += 0x100;
        }
        table[index] = (low >> 8) as u8;
        let limit = i32::from(self.script_starts[index + 1]);
        ((low & 0xff00) + ((limit & 0xff00) - (start & 0xff00))) | (limit & 0xff)
    }

    fn add_high(&self, table: &mut [u8; 256], index: usize, mut high: i32) -> i32 {
        let limit = i32::from(self.script_starts[index + 1]);
        if limit & 0xff > high & 0xff {
            high -= 0x100;
        }
        let start = i32::from(self.script_starts[index]);
        high = ((high & 0xff00) - ((limit & 0xff00) - (start & 0xff00))) | (start & 0xff);
        table[index] = (high >> 8) as u8;
        high
    }
}

fn read_header(reader: &mut Reader<'_>, magic: &[u8; 8]) -> Result<()> {
    if reader.take(8)? != magic || reader.u32()? != 1 {
        return Err(Error::Data("unsupported settings/scripts magic/schema"));
    }
    for expected in [77, 1, 16, 0, 47, 0] {
        if reader.u32()? != expected {
            return Err(Error::Data("expected ICU 77.1 / Unicode 16.0 / CLDR 47.0"));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rejects(fields: Reordering77) {
        assert!(matches!(
            Reordering77::from_icu(
                fields.codes,
                fields.table,
                fields.min_high_no_reorder,
                fields.ranges,
            ),
            Err(Error::Data(_))
        ));
    }

    #[test]
    fn missing_split_ranges_are_rejected_before_collation() {
        let mut missing = Reordering77 {
            codes: vec![14],
            table: [0; 256],
            min_high_no_reorder: 0xff00_0000,
            ranges: Vec::new(),
        };
        missing.table[..3].copy_from_slice(&[0, 1, 2]);
        rejects(missing.clone());
        // A correct trailing-weight slot does not excuse missing used ranges.
        missing.table[255] = 255;
        rejects(missing);

        let settings =
            Settings77::from_bytes(include_bytes!("../../data/locales/settings-0002.bin")).unwrap();
        let mut missing = settings.reordering().unwrap().clone();
        missing.ranges.clear();
        rejects(missing);
    }

    #[test]
    fn retained_range_boundaries_and_table_suffix_must_agree() {
        let settings =
            Settings77::from_bytes(include_bytes!("../../data/locales/settings-0002.bin")).unwrap();
        let valid = settings.reordering().unwrap();
        let mut missing_first_split = valid.clone();
        missing_first_split.ranges.remove(0);
        rejects(missing_first_split);

        let mut hidden_split = valid.clone();
        hidden_split.table[0x68] = 0x68;
        rejects(hidden_split);

        let mut unexplained_zero = valid.clone();
        unexplained_zero.table[0x33] = 0;
        rejects(unexplained_zero);

        let mut changed_suffix = valid.clone();
        changed_suffix.table[0x6a] = 0x6b;
        rejects(changed_suffix);

        let mut zero_last_offset = valid.clone();
        *zero_last_offset.ranges.last_mut().unwrap() &= 0xffff_0000;
        rejects(zero_last_offset);

        let mut invalid_target = valid.clone();
        invalid_target.ranges[0] = (invalid_target.ranges[0] & 0xffff_0000) | 255;
        rejects(invalid_target);
    }

    #[test]
    fn frozen_unused_zero_slots_remain_valid() {
        // These fields were exported from ICU77, including the zero slot in
        // a reserved lead before the retained split ranges in settings-0406.
        for bytes in [
            &include_bytes!("../../data/locales/settings-0422.bin")[..],
            &include_bytes!("../../data/locales/settings-0406.bin")[..],
        ] {
            Settings77::from_bytes(bytes).unwrap();
        }
    }
}
