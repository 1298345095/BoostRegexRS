// Development-only ICU77 FCD cursor diagnostic; no CE lookup or sort-key writer.
// ICU provenance: ../data/NOTICE.md and ../data/LICENSE-ICU.txt.
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unicode/coll.h>
#include <unicode/uversion.h>
#include <unicode/utf16.h>
#include "collationfcd.h"
#include "collationtailoring.h"
#include "normalizer2impl.h"
#include "ucol_imp.h"
#include "utf16collationiterator.h"

namespace {
std::vector<char16_t> parse(const std::string& text) {
    std::vector<char16_t> result;
    std::istringstream fields(text);
    std::string field;
    while (std::getline(fields, field, ',')) {
        if (field.empty() || field.size() > 4 || field.find_first_not_of("0123456789abcdefABCDEF") != std::string::npos) {
            throw std::runtime_error("Expected ASCII hexadecimal UTF-16 units");
        }
        result.push_back(static_cast<char16_t>(std::stoul(field, nullptr, 16)));
    }
    if (!text.empty() && text.back() == ',') throw std::runtime_error("Trailing input separator");
    if (result.size() > static_cast<size_t>(std::numeric_limits<int32_t>::max())) throw std::runtime_error("Input exceeds ICU length domain");
    return result;
}

void direction(icu::FCDUTF16CollationIterator& iterator, const std::string& id, const char* label, bool forward) {
    UErrorCode status = U_ZERO_ERROR;
    for (size_t index = 0;; ++index) {
        const auto cp = forward ? iterator.nextCodePoint(status) : iterator.previousCodePoint(status);
        if (U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
        std::cout << id << '\t' << label << '\t' << index << '\t';
        if (cp >= 0) std::cout << std::hex << std::setw(6) << std::setfill('0') << cp << std::dec;
        std::cout << '\t' << iterator.getOffset() << '\t' << (cp < 0 ? 1 : 0) << '\n';
        if (cp < 0) break;
    }
}

void fcd_values(const icu::CollationData& data, const std::string& id, const std::vector<char16_t>& units, int32_t length) {
    const char16_t* begin = units.data();
    const char16_t* cursor = begin;
    const char16_t* limit = begin + length;
    size_t index = 0;
    while (cursor != limit) {
        const char16_t* before = cursor;
        const auto value = data.nfcImpl.nextFCD16(cursor, limit);
        int32_t offset = static_cast<int32_t>(before - begin);
        UChar32 cp;
        U16_NEXT(begin, offset, length, cp);
        std::cout << id << '\t' << index++ << '\t' << before - begin << '\t' << cursor - begin << '\t'
                  << std::hex << std::setw(6) << std::setfill('0') << cp << '\t'
                  << std::setw(4) << data.getFCD16(cp) << '\t' << std::setw(4) << value << std::dec << '\t'
                  << int(icu::CollationFCD::hasTccc(*before)) << '\t'
                  << int(before + 1 != limit && icu::CollationFCD::hasLccc(before[1])) << '\n';
    }
}

void trace(const char* locale, bool values) {
    UVersionInfo version;
    u_getVersion(version);
    if (version[0] != 77 || version[1] != 1) throw std::runtime_error("ICU77.1 is required");
    UErrorCode status = U_ZERO_ERROR;
    const auto name = icu::Locale::createFromName(locale);
    const auto release = [](const icu::CollationCacheEntry* entry) { if (entry) entry->removeRef(); };
    std::unique_ptr<const icu::CollationCacheEntry, decltype(release)> entry(icu::CollationLoader::loadTailoring(name, status), release);
    std::unique_ptr<icu::Collator> collator(icu::Collator::createInstance(name, status));
    if (U_FAILURE(status) || !entry || !collator) throw std::runtime_error(u_errorName(status));
    const auto normalization = collator->getAttribute(UCOL_NORMALIZATION_MODE, status);
    const auto numeric = collator->getAttribute(UCOL_NUMERIC_COLLATION, status);
    if (U_FAILURE(status) || normalization != UCOL_ON) throw std::runtime_error("FCD diagnostic requires the locale's actual normalization ON");
    std::string line;
    if (!std::getline(std::cin, line) || line != "case_id\tu16_hex") throw std::runtime_error("Invalid UTF-16 TSV header");
    std::cout << (values ? "case_id\tindex\tutf16_before\tutf16_after\tcode_point_hex\tdata_fcd16_hex\tnext_fcd16_hex\tfirst_unit_has_tccc\tfollowing_unit_has_lccc\n"
                        : "case_id\tdirection\tindex\tcode_point_hex\tutf16_offset_after\tterminal\n");
    while (std::getline(std::cin, line)) {
        const auto tab = line.find('\t');
        if (tab == 0 || tab == std::string::npos || line.find('\t', tab + 1) != std::string::npos) throw std::runtime_error("Expected two TSV columns");
        auto units = parse(line.substr(tab + 1));
        const auto length = static_cast<int32_t>(units.size());
        units.push_back(0);
        const auto id = line.substr(0, tab);
        if (values) {
            fcd_values(*entry->tailoring->data, id, units, length);
            continue;
        }
        icu::FCDUTF16CollationIterator iterator(entry->tailoring->data, numeric == UCOL_ON,
                                               units.data(), units.data(), units.data() + length);
        direction(iterator, id, "forward-1", true);
        direction(iterator, id, "backward", false);
        direction(iterator, id, "forward-2", true);
    }
    if (std::cin.bad() || !std::cout.good()) throw std::runtime_error("FCD trace stream failed");
}

void flags() {
    UVersionInfo version;
    u_getVersion(version);
    if (version[0] != 77 || version[1] != 1) throw std::runtime_error("ICU77.1 is required");
    for (int32_t unit = 0; unit <= 0xffff; ++unit) {
        const auto value = unsigned(icu::CollationFCD::hasLccc(unit)) |
                           (unsigned(icu::CollationFCD::hasTccc(unit)) << 1);
        std::cout.put(static_cast<char>(value));
    }
    if (!std::cout.good()) throw std::runtime_error("FCD flag output failed");
}
}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--fcd-flags") {
        try { flags(); return 0; }
        catch (const std::exception& error) { std::cerr << "trace-fcd: " << error.what() << '\n'; return 1; }
    }
    const bool values = argc == 3 && std::string(argv[2]) == "--fcd-values";
    if (argc != 2 && !values) { std::cerr << "usage: trace-fcd ICU_LOCALE [--fcd-values] < input-u16.tsv\n"; return 2; }
    try { trace(argv[1], values); return 0; }
    catch (const std::exception& error) { std::cerr << "trace-fcd: " << error.what() << '\n'; return 1; }
}
