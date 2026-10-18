// Development-only ICU4C 77.1 CE diagnostic with the locale's actual FCD/numeric settings.
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
#include <unicode/tblcoll.h>
#include <unicode/uversion.h>
#include "collation.h"
#include "uvectr64.h"

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This diagnostic requires official ICU4C 77.1 headers.
#endif

namespace {
std::vector<char16_t> parse_units(const std::string& text) {
    std::vector<char16_t> units;
    std::istringstream fields(text);
    std::string field;
    while (std::getline(fields, field, ',')) {
        if (field.empty() || field.size() > 4) throw std::runtime_error("Expected one to four ASCII hex digits per UTF-16 unit");
        for (char ch : field) {
            if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f') || (ch >= 'A' && ch <= 'F'))) {
                throw std::runtime_error("Non-ASCII hexadecimal UTF-16 unit");
            }
        }
        units.push_back(static_cast<char16_t>(std::stoul(field, nullptr, 16)));
    }
    if (!text.empty() && text.back() == ',') throw std::runtime_error("Trailing comma in UTF-16 input");
    if (units.size() > static_cast<size_t>(std::numeric_limits<int32_t>::max())) throw std::runtime_error("Input exceeds ICU's length domain");
    return units;
}

void trace(const char* locale) {
    UVersionInfo version;
    u_getVersion(version);
    if (version[0] != 77 || version[1] != 1) throw std::runtime_error("Runtime ICU must be 77.1");
    UErrorCode status = U_ZERO_ERROR;
    std::unique_ptr<icu::Collator> base(icu::Collator::createInstance(icu::Locale::createFromName(locale), status));
    auto* collator = dynamic_cast<icu::RuleBasedCollator*>(base.get());
    if (U_FAILURE(status) || collator == nullptr) throw std::runtime_error(u_errorName(status));
    std::string line;
    if (!std::getline(std::cin, line) || line != "case_id\tu16_hex") throw std::runtime_error("Expected case_id<TAB>u16_hex header");
    std::cout << "case_id\tces64_hex\n";
    while (std::getline(std::cin, line)) {
        const auto tab = line.find('\t');
        if (tab == std::string::npos || tab == 0 || line.find('\t', tab + 1) != std::string::npos) throw std::runtime_error("Expected exactly two TSV columns");
        auto units = parse_units(line.substr(tab + 1));
        const auto length = static_cast<int32_t>(units.size());
        units.push_back(0);  // Valid address also for a zero explicit length.
        status = U_ZERO_ERROR;
        icu::UVector64 ces(status);
        collator->internalGetCEs(icu::UnicodeString(units.data(), length), ces, status);
        if (U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
        std::cout << line.substr(0, tab) << '\t' << std::hex << std::setfill('0');
        for (int32_t i = 0; i < ces.size(); ++i) {
            std::cout << std::setw(16) << static_cast<uint64_t>(ces.elementAti(i)) << ',';
        }
        // internalGetCEs stops after reading NO_CE without appending it. Restore
        // that successful termination marker to match the Rust iterator trace.
        std::cout << std::setw(16) << static_cast<uint64_t>(icu::Collation::NO_CE) << std::dec << '\n';
    }
    if (std::cin.bad() || !std::cout.good()) throw std::runtime_error("Trace stream failed");
}
}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: trace-locale ICU_LOCALE < input-u16.tsv\n"; return 2; }
    try { trace(argv[1]); return 0; }
    catch (const std::exception& error) { std::cerr << "trace-locale: " << error.what() << '\n'; return 1; }
}
