// Development-only, unmodified Boost.Regex 1.89.0 / ICU4C 77.1 oracle.
// Dependencies remain external. Boost: BSL-1.0; ICU: Unicode-3.0.
#define BOOST_REGEX_NO_LIB
#include <boost/regex/icu.hpp>
#include <boost/version.hpp>
#include <unicode/icudataver.h>
#include <unicode/ulocdata.h>
#include <unicode/uversion.h>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
template<class Values> std::string hex(const Values& values, int width) {
    std::ostringstream out;
    bool first = true;
    for (auto value : values) {
        if (!first) out << ',';
        first = false;
        out << std::hex << std::setfill('0') << std::setw(width)
            << static_cast<std::uint32_t>(value);
    }
    return out.str();
}

std::string json_string(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (const unsigned char ch : value) {
        if (ch == '"' || ch == '\\') out << '\\' << ch;
        else if (ch < 0x20) out << "\\u" << std::hex << std::setfill('0') << std::setw(4) << unsigned(ch);
        else out << ch;
    }
    out << '"';
    return out.str();
}

std::uint32_t number(const std::string& value, std::size_t width) {
    if (value.size() != width || value.find_first_not_of("0123456789abcdefABCDEF") != std::string::npos)
        throw std::invalid_argument("Malformed hexadecimal input");
    return static_cast<std::uint32_t>(std::stoull(value, nullptr, 16));
}

template<class T> std::vector<T> units(const std::string& value, std::size_t width) {
    std::vector<T> result;
    if (value.empty()) return result;
    std::size_t begin = 0;
    while (begin < value.size()) {
        auto end = value.find(',', begin);
        if (end == std::string::npos) end = value.size();
        result.push_back(static_cast<T>(number(value.substr(begin, end - begin), width)));
        begin = end + 1;
        if (begin == value.size()) throw std::invalid_argument("Trailing comma");
    }
    return result;
}

std::vector<UChar32> decode(const std::string& value, const std::string& format) {
    if (format == "u32") return units<UChar32>(value, 8);
    if (format == "u16") {
        const auto input = units<UChar>(value, 4);
        using Iterator = boost::u16_to_u32_iterator<std::vector<UChar>::const_iterator, UChar32>;
        return {Iterator(input.begin(), input.begin(), input.end()),
                Iterator(input.end(), input.begin(), input.end())};
    }
    if (value.size() % 2 != 0) throw std::invalid_argument("Odd UTF-8 hex length");
    std::vector<std::uint8_t> input;
    for (std::size_t i = 0; i < value.size(); i += 2)
        input.push_back(static_cast<std::uint8_t>(number(value.substr(i, 2), 2)));
    using Iterator = boost::u8_to_u32_iterator<std::vector<std::uint8_t>::const_iterator, UChar32>;
    return {Iterator(input.begin(), input.begin(), input.end()),
            Iterator(input.end(), input.begin(), input.end())};
}

void check_versions() {
    UErrorCode status = U_ZERO_ERROR;
    UVersionInfo runtime{}, unicode{}, cldr{}, data{};
    u_getVersion(runtime);
    u_getUnicodeVersion(unicode);
    ulocdata_getCLDRVersion(cldr, &status);
    u_getDataVersion(data, &status);
    if (U_FAILURE(status) || BOOST_VERSION != 108900 || runtime[0] != 77 || runtime[1] != 1 ||
        unicode[0] != 16 || unicode[1] != 0 || cldr[0] != 47 || data[0] != 77 || data[1] != 1)
        throw std::runtime_error("Unexpected Boost / ICU / Unicode / CLDR / data version");
}
} // namespace

int main(int argc, char** argv) try {
    std::string format = "utf8";
    std::string strength = "primary";
    std::string locale_name = "root";
    std::string metadata_path;
    bool order_pairs = false;
    bool approved_empty = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--input-format" && i + 1 < argc) format = argv[++i];
        else if (arg == "--strength" && i + 1 < argc) strength = argv[++i];
        else if (arg == "--locale" && i + 1 < argc) locale_name = argv[++i];
        else if (arg == "--metadata" && i + 1 < argc) metadata_path = argv[++i];
        else if (arg == "--approved-empty-exception") approved_empty = true;
        else if (arg == "--order-pairs") order_pairs = true;
        else throw std::invalid_argument("usage: oracle [--input-format utf8|u32|u16] [--strength primary|identical] [--locale ICU_ID] [--approved-empty-exception] [--metadata PATH] [--order-pairs]");
    }
    if (format != "utf8" && format != "u32" && format != "u16") throw std::invalid_argument("Unknown input format");
    if (strength != "primary" && strength != "identical") throw std::invalid_argument("Unknown strength");
    if (approved_empty && strength != "identical") throw std::invalid_argument("Approved empty exception is IDENTICAL only");
    check_versions();
    UErrorCode status = U_ZERO_ERROR;
    const auto locale = icu::Locale::createFromName(locale_name.c_str());
    std::unique_ptr<icu::Collator> collator(icu::Collator::createInstance(locale, status));
    if (U_FAILURE(status) || !collator) throw std::runtime_error(std::string("Collator creation failed: ") + u_errorName(status));
    const auto creation_status = status;
    collator->setStrength(strength == "identical" ? icu::Collator::IDENTICAL : icu::Collator::PRIMARY);
    if (locale_name == "root" && (collator->getAttribute(UCOL_NORMALIZATION_MODE, status) != UCOL_OFF || U_FAILURE(status)))
        throw std::runtime_error("Unexpected root normalization setting");
    boost::icu_regex_traits traits;
    traits.imbue(locale);
    if (!metadata_path.empty()) {
        std::ofstream metadata(metadata_path);
        metadata << "{\n  \"boost\": \"1.89.0\", \"icu\": \"77.1\", \"unicode\": \"16.0.0\", \"cldr\": \"47.0\",\n"
                 << "  \"locale\": " << json_string(locale_name) << ", \"strength\": \"" << strength << "\",\n"
                 << "  \"normalized_locale\": " << json_string(locale.getName()) << ",\n"
                 << "  \"valid_locale\": " << json_string(collator->getLocale(ULOC_VALID_LOCALE, status).getName()) << ",\n"
                 << "  \"actual_locale\": " << json_string(collator->getLocale(ULOC_ACTUAL_LOCALE, status).getName()) << ",\n"
                 << "  \"creation_status\": " << json_string(u_errorName(creation_status)) << ",\n"
                 << "  \"traits_getloc\": " << json_string(traits.getloc().getName()) << ",\n"
                 << "  \"process_default_locale\": " << json_string(icu::Locale::getDefault().getName()) << ",\n"
                 << "  \"approved_empty_exception\": " << (approved_empty ? "true" : "false") << ",\n  \"attributes\": {";
        const std::pair<const char*, UColAttribute> attributes[] = {
            {"strength", UCOL_STRENGTH}, {"normalization", UCOL_NORMALIZATION_MODE},
            {"numeric", UCOL_NUMERIC_COLLATION}, {"alternate", UCOL_ALTERNATE_HANDLING},
            {"case_level", UCOL_CASE_LEVEL}, {"case_first", UCOL_CASE_FIRST},
            {"french_secondary", UCOL_FRENCH_COLLATION}, {"hiragana_quaternary", UCOL_HIRAGANA_QUATERNARY_MODE},
        };
        bool first = true;
        for (const auto& attribute : attributes) {
            metadata << (first ? "\n" : ",\n") << "    \"" << attribute.first << "\": "
                     << collator->getAttribute(attribute.second, status);
            first = false;
        }
        metadata << "\n  },\n  \"variable_top\": " << collator->getVariableTop(status)
                 << ", \"max_variable\": " << collator->getMaxVariable() << ",\n  \"reorder_codes\": [";
        int32_t count = collator->getReorderCodes(nullptr, 0, status);
        if (status == U_BUFFER_OVERFLOW_ERROR) status = U_ZERO_ERROR;
        if (U_FAILURE(status) || count < 0) throw std::runtime_error("Oracle reorder preflight failed");
        std::vector<int32_t> codes(static_cast<std::size_t>(count));
        if (collator->getReorderCodes(codes.data(), count, status) != count || U_FAILURE(status))
            throw std::runtime_error("Oracle reorder preflight changed");
        for (int32_t i = 0; i < count; ++i) metadata << (i ? "," : "") << codes[i];
        metadata << "]\n}\n";
        metadata.flush();
        if (U_FAILURE(status) || !metadata) throw std::runtime_error("Oracle metadata write failed");
    }
    std::ios::sync_with_stdio(false);
    std::cout << (order_pairs ? "left_id\tright_id\tordering\n" : "case_id\traw_icu_hex\tboost_u32_hex\n");
    std::string line;
    std::vector<UChar> previous;
    std::string previous_id;
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        const auto tab = line.find('\t');
        if (tab == std::string::npos || tab == 0 || line.find('\t', tab + 1) != std::string::npos)
            throw std::invalid_argument("Expected two TSV columns");
        const auto id = line.substr(0, tab);
        const auto value = line.substr(tab + 1);
        if (id == "case_id" && (value == "utf8_hex" || value == "u32_hex" || value == "u16_hex")) continue;
        try {
            const auto scalars = decode(value, format);
            const UChar32 sentinel = 0;
            const auto* first = scalars.empty() ? &sentinel : scalars.data();
            using Iterator = boost::u32_to_u16_iterator<const UChar32*, UChar>;
            const std::vector<UChar> utf16(Iterator(first), Iterator(first + scalars.size()));
            const UChar empty = 0;
            const auto* input = utf16.empty() ? &empty : utf16.data();
            if (order_pairs) {
                if (!previous_id.empty()) {
                    const auto* left = previous.empty() ? &empty : previous.data();
                    status = U_ZERO_ERROR;
                    const auto result = collator->compare(left, static_cast<std::int32_t>(previous.size()),
                                                          input, static_cast<std::int32_t>(utf16.size()), status);
                    if (U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
                    std::cout << previous_id << '\t' << id << '\t' << ((result > 0) - (result < 0)) << '\n';
                }
                previous = utf16;
                previous_id = id;
                continue;
            }
            const auto length = collator->getSortKey(input, static_cast<std::int32_t>(utf16.size()), nullptr, 0);
            if (length <= 0) throw std::runtime_error("Invalid ICU key length");
            std::vector<std::uint8_t> raw(static_cast<std::size_t>(length));
            if (collator->getSortKey(input, static_cast<std::int32_t>(utf16.size()), raw.data(), length) != length)
                throw std::runtime_error("ICU key preflight changed");
            // This is the actual unmodified Boost call, including its stack/heap
            // buffer paths. The valid-pointer ICU call above is independent.
            std::vector<UChar32> key;
            if (approved_empty && scalars.empty()) {
                // ADR-0005 only: independently computed valid-pointer ICU bytes,
                // then the documented Boost byte-per-u32 convention. The runner
                // records the original crashing call separately, never as a pass.
                key.assign(raw.begin(), raw.end());
                if (key.size() > 1 && key.back() == 0) key.pop_back();
            } else {
                key = strength == "identical" ? traits.transform(first, first + scalars.size())
                                               : traits.transform_primary(first, first + scalars.size());
            }
            std::cout << id << '\t' << hex(raw, 2) << '\t' << hex(key, 8) << '\n';
        } catch (const std::out_of_range&) {
            if (order_pairs) throw;
            const auto error = format == "u32" ? "ERROR:INVALID_UTF32" :
                               format == "u16" ? "ERROR:INVALID_UTF16" : "ERROR:INVALID_UTF8";
            std::cout << id << '\t' << error << '\t' << error << '\n';
        }
    }
    if (!std::cin.eof() || !std::cout) throw std::runtime_error("I/O failure");
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 2;
}
