// Development-only ICU4C 77.1 64-bit CE diagnostic.
// ICU algorithm/data provenance: ../data/NOTICE.md and LICENSE-ICU.txt.

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "unicode/uchar.h"
#include "unicode/utf16.h"
#include "unicode/uversion.h"
#include "collation.h"
#include "collationdata.h"
#include "collationroot.h"
#include "collationsettings.h"
#include "utf16collationiterator.h"

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This trace program requires official ICU4C 77.1 headers.
#endif

namespace {

std::vector<char16_t> parseUnits(const std::string& source) {
    std::vector<char16_t> units;
    if (source.empty()) {
        return units;
    }
    std::istringstream fields(source);
    std::string field;
    while (std::getline(fields, field, ',')) {
        if (field.empty() || field.size() > 4) {
            throw std::runtime_error("UTF-16 units must be one to four hex digits");
        }
        for (char c : field) {
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) {
                throw std::runtime_error("invalid hexadecimal UTF-16 unit");
            }
        }
        units.push_back(static_cast<char16_t>(std::stoul(field, nullptr, 16)));
    }
    if (source.back() == ',') {
        throw std::runtime_error("trailing comma in UTF-16 input");
    }
    return units;
}

void trace(std::vector<char16_t> units) {
    UVersionInfo version;
    u_getVersion(version);
    if (version[0] != 77 || version[1] != 1) {
        throw std::runtime_error("runtime ICU version must be 77.1");
    }
    UErrorCode status = U_ZERO_ERROR;
    const auto* data = icu::CollationRoot::getData(status);
    const auto* settings = icu::CollationRoot::getSettings(status);
    if (U_FAILURE(status) || data == nullptr || settings == nullptr ||
        !settings->dontCheckFCD() || settings->isNumeric()) {
        throw std::runtime_error("unexpected root data/settings");
    }
    const auto length = static_cast<int32_t>(units.size());
    units.push_back(0);  // A valid pointer also for empty input; limit remains explicit.
    icu::UTF16CollationIterator iterator(data, false, units.data(), units.data(),
                                        units.data() + length);
    std::cout << "{\n  \"engine\": \"ICU4C 77.1 UTF16CollationIterator\","
                 "\n  \"locale\": \"root\",\n  \"normalization\": \"OFF\","
                 "\n  \"numeric\": \"OFF\",\n  \"input_utf16\": [";
    for (int32_t i = 0; i < length; ++i) {
        std::cout << (i == 0 ? "" : ",") << static_cast<uint32_t>(units[i]);
    }
    std::cout << "],\n  \"lookups\": [";
    int32_t offset = 0;
    bool first = true;
    while (offset < length) {
        UChar32 cp;
        U16_NEXT(units.data(), offset, length, cp);
        std::cout << (first ? "\n" : ",\n") << "    {\"codepoint\": " << cp
                  << ", \"ce32\": \"" << std::hex << std::setfill('0') << std::setw(8)
                  << data->getCE32(cp) << std::dec << "\", \"fcd16\": " << data->getFCD16(cp)
                  << '}';
        first = false;
    }
    std::cout << "\n  ],\n  \"ces\": [";
    first = true;
    for (;;) {
        const int64_t ce = iterator.nextCE(status);
        if (U_FAILURE(status)) {
            throw std::runtime_error(u_errorName(status));
        }
        std::cout << (first ? "\n" : ",\n") << "    {\"ce64\": \"" << std::hex
                  << std::setfill('0') << std::setw(16) << static_cast<uint64_t>(ce)
                  << "\", \"primary32\": \"" << std::setw(8)
                  << static_cast<uint32_t>(static_cast<uint64_t>(ce) >> 32)
                  << std::dec << "\", \"utf16_offset_after\": " << iterator.getOffset()
                  << ", \"sentinel\": " << (ce == icu::Collation::NO_CE ? "true" : "false") << '}';
        first = false;
        if (ce == icu::Collation::NO_CE) {
            break;
        }
    }
    std::cout << "\n  ]\n}\n";
}

void traceBatch() {
    UVersionInfo version;
    u_getVersion(version);
    if (version[0] != 77 || version[1] != 1) {
        throw std::runtime_error("runtime ICU version must be 77.1");
    }
    UErrorCode status = U_ZERO_ERROR;
    const auto* data = icu::CollationRoot::getData(status);
    const auto* settings = icu::CollationRoot::getSettings(status);
    if (U_FAILURE(status) || data == nullptr || settings == nullptr ||
        !settings->dontCheckFCD() || settings->isNumeric()) {
        throw std::runtime_error("unexpected root data/settings");
    }
    std::cout << "case_id\tces64_hex\n";
    std::string line;
    bool firstLine = true;
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (firstLine && line == "case_id\tu16_hex") {
            firstLine = false;
            continue;
        }
        firstLine = false;
        const size_t split = line.find('\t');
        if (split == std::string::npos || split == 0 || line.find('\t', split + 1) != std::string::npos) {
            throw std::runtime_error("batch input must contain exactly case_id<TAB>u16_hex");
        }
        const std::string caseId = line.substr(0, split);
        auto units = parseUnits(line.substr(split + 1));
        const auto length = static_cast<int32_t>(units.size());
        units.push_back(0);
        icu::UTF16CollationIterator iterator(data, false, units.data(), units.data(),
                                            units.data() + length);
        std::cout << caseId << '\t';
        bool first = true;
        for (;;) {
            const int64_t ce = iterator.nextCE(status);
            if (U_FAILURE(status)) {
                throw std::runtime_error(u_errorName(status));
            }
            std::cout << (first ? "" : ",") << std::hex << std::setfill('0') << std::setw(16)
                      << static_cast<uint64_t>(ce) << std::dec;
            first = false;
            if (ce == icu::Collation::NO_CE) {
                break;
            }
        }
        std::cout << '\n';
    }
    if (std::cin.bad()) {
        throw std::runtime_error("failed to read trace batch");
    }
}

}  // namespace

int main(int argc, char** argv) {
    const bool batch = argc == 2 && std::string(argv[1]) == "--batch-utf16";
    if (!batch && (argc != 3 || std::string(argv[1]) != "--utf16")) {
        std::cerr << "usage: trace-root --utf16 0061,0315,0300 | --batch-utf16\n";
        return 2;
    }
    try {
        if (batch) {
            traceBatch();
        } else {
            trace(parseUnits(argv[2]));
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "trace-root: " << error.what() << '\n';
        return 1;
    }
}
