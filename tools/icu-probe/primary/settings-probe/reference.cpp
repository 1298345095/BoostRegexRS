// Development-only public ICU77 reorder setter and all-strength key reference.
// Fixed ICU data/source provenance: ../data/NOTICE.md and ../data/LICENSE-ICU.txt.
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unicode/coll.h>
#include <unicode/uchar.h>
#include <unicode/ulocdata.h>
#include <unicode/uversion.h>

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This reference requires official ICU4C 77.1 headers.
#endif

namespace {
void require(bool condition, const char* reason) {
    if (!condition) throw std::runtime_error(reason);
}

std::vector<std::string> split(const std::string& text, char separator) {
    std::vector<std::string> values;
    size_t start = 0;
    for (;;) {
        const auto next = text.find(separator, start);
        values.push_back(text.substr(start, next == std::string::npos ? next : next - start));
        if (next == std::string::npos) return values;
        start = next + 1;
    }
}

std::vector<int32_t> codes(const std::string& text) {
    if (text.empty()) return {};
    std::vector<int32_t> result;
    for (const auto& item : split(text, ',')) {
        size_t consumed = 0;
        const auto value = std::stoll(item, &consumed);
        require(consumed == item.size() && value >= INT32_MIN && value <= INT32_MAX,
                "Invalid decimal i32 reorder code");
        result.push_back(static_cast<int32_t>(value));
    }
    return result;
}

std::vector<char16_t> units(const std::string& text) {
    if (text.empty()) return {};
    std::vector<char16_t> result;
    for (const auto& item : split(text, ',')) {
        require(!item.empty() && item.size() <= 4, "Invalid UTF-16 input unit");
        for (char ch : item) require((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'), "Invalid UTF-16 hex digit");
        result.push_back(static_cast<char16_t>(std::stoul(item, nullptr, 16)));
    }
    require(result.size() <= static_cast<size_t>(INT32_MAX), "Input exceeds ICU's length domain");
    return result;
}

std::string current_codes(const icu::Collator& collator) {
    UErrorCode status = U_ZERO_ERROR;
    const auto count = collator.getReorderCodes(nullptr, 0, status);
    if (status == U_BUFFER_OVERFLOW_ERROR) status = U_ZERO_ERROR;
    require(U_SUCCESS(status) && count >= 0, "Cannot preflight reorder codes");
    std::vector<int32_t> values(static_cast<size_t>(count));
    require(collator.getReorderCodes(values.data(), count, status) == count && U_SUCCESS(status),
            "Cannot obtain complete reorder codes");
    std::string result;
    for (auto value : values) {
        if (!result.empty()) result += ',';
        result += std::to_string(value);
    }
    return result;
}

std::string key(icu::Collator& collator, const std::vector<char16_t>& text, int32_t length, int strength) {
    collator.setStrength(static_cast<icu::Collator::ECollationStrength>(strength));
    const auto required = collator.getSortKey(text.data(), length, nullptr, 0);
    require(required > 0, "Native key preflight failed");
    std::vector<uint8_t> bytes(static_cast<size_t>(required));
    require(collator.getSortKey(text.data(), length, bytes.data(), required) == required && bytes.back() == 0,
            "Native key is incomplete or changed after preflight");
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (auto byte : bytes) out << std::setw(2) << static_cast<unsigned>(byte);
    return out.str();
}

void versions() {
    UVersionInfo runtime{}, unicode{}, cldr{};
    UErrorCode status = U_ZERO_ERROR;
    u_getVersion(runtime);
    u_getUnicodeVersion(unicode);
    ulocdata_getCLDRVersion(cldr, &status);
    require(U_SUCCESS(status) && runtime[0] == 77 && runtime[1] == 1 &&
            unicode[0] == 16 && unicode[1] == 0 && cldr[0] == 47 && cldr[1] == 0,
            "Unexpected ICU/Unicode/CLDR version");
}

void metadata(const icu::Collator& collator, const char* filename) {
    UErrorCode status = U_ZERO_ERROR;
    std::ofstream out(filename);
    require(out.good(), "Cannot create settings reference metadata");
    out << "{\"icu\":\"77.1\",\"unicode\":\"16.0.0\",\"cldr\":\"47.0\",\"attributes\":{";
    const std::pair<const char*, UColAttribute> attributes[] = {
        {"strength", UCOL_STRENGTH}, {"normalization", UCOL_NORMALIZATION_MODE},
        {"numeric", UCOL_NUMERIC_COLLATION}, {"alternate", UCOL_ALTERNATE_HANDLING},
        {"case_level", UCOL_CASE_LEVEL}, {"case_first", UCOL_CASE_FIRST},
        {"french_secondary", UCOL_FRENCH_COLLATION},
    };
    bool first = true;
    for (const auto& attribute : attributes) {
        out << (first ? "" : ",") << '"' << attribute.first << "\":" << collator.getAttribute(attribute.second, status);
        first = false;
    }
    out << "},\"variable_top\":" << collator.getVariableTop(status)
        << ",\"reorder_codes\":[" << current_codes(collator) << "]}\n";
    out.flush();
    require(out.good() && U_SUCCESS(status), "Cannot record native effective settings");
}

void run(const char* locale, const char* metadata_path) {
    versions();
    UErrorCode status = U_ZERO_ERROR;
    std::unique_ptr<icu::Collator> defaults(icu::Collator::createInstance(icu::Locale::createFromName(locale), status));
    require(defaults && U_SUCCESS(status), "Native locale creation failed");
    metadata(*defaults, metadata_path);
    std::string line;
    require(std::getline(std::cin, line) && line == "case_id\tsetup_codes\trequest_codes\tu16_hex",
            "Invalid settings probe input header");
    std::cout << "case_id\tstatus\timplementation_error\tbefore_codes\tafter_codes\tbefore_primary\tbefore_identical"
                 "\tprimary\tsecondary\ttertiary\tquaternary\tidentical\n";
    while (std::getline(std::cin, line)) {
        const auto fields = split(line, '\t');
        require(fields.size() == 4 && !fields[0].empty(), "Settings input requires four TSV fields");
        auto text = units(fields[3]);
        const auto length = static_cast<int32_t>(text.size());
        text.push_back(0);  // Valid explicit-length pointer for the empty input.
        std::unique_ptr<icu::Collator> collator(defaults->clone());
        require(bool(collator), "Cannot clone native settings profile");
        if (fields[1] != "~") {
            const auto setup = codes(fields[1]);
            status = U_ZERO_ERROR;
            collator->setReorderCodes(setup.data(), static_cast<int32_t>(setup.size()), status);
            require(U_SUCCESS(status), "Generated setup reorder list was rejected");
        }
        const auto before_codes = current_codes(*collator);
        const auto before_primary = key(*collator, text, length, UCOL_PRIMARY);
        const auto before_identical = key(*collator, text, length, UCOL_IDENTICAL);
        status = U_ZERO_ERROR;
        if (fields[2] != "~") {
            const auto requested = codes(fields[2]);
            collator->setReorderCodes(requested.data(), static_cast<int32_t>(requested.size()), status);
        }
        std::cout << fields[0] << '\t' << u_errorName(status) << '\t'
                  << (U_FAILURE(status) ? u_errorName(status) : "") << '\t'
                  << before_codes << '\t' << current_codes(*collator) << '\t'
                  << before_primary << '\t' << before_identical;
        for (auto strength : {UCOL_PRIMARY, UCOL_SECONDARY, UCOL_TERTIARY, UCOL_QUATERNARY, UCOL_IDENTICAL}) {
            std::cout << '\t' << key(*collator, text, length, strength);
        }
        std::cout << '\n';
    }
    require(!std::cin.bad() && std::cout.good(), "Settings reference stream failed");
}
}  // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 3, "usage: settings-reference ICU_LOCALE METADATA.json < input.tsv");
        run(argv[1], argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "settings-reference: " << error.what() << '\n';
        return 1;
    }
}
