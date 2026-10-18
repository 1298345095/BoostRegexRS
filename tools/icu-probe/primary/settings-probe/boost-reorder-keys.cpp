// Public Boost locale/traits reference for complete keys with internal NUL.
// ICU is only a development reference. No private headers or source patches.
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <boost/regex/icu.hpp>
#include <boost/version.hpp>
#include <unicode/uscript.h>

#if BOOST_VERSION != 108900 || U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This reference requires official Boost 1.89.0 and ICU4C 77.1.
#endif

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

static std::vector<std::string> split(const std::string& text, char separator) {
    std::vector<std::string> result;
    std::istringstream input(text);
    for (std::string field; std::getline(input, field, separator);) result.push_back(field);
    return result;
}

static std::string locale_name(const std::string& requested) {
    std::string result = "root@colReorder=";
    bool first = true;
    for (const auto& item : split(requested, ',')) {
        const auto code = std::stoi(item);
        const char* name = nullptr;
        if (code >= UCOL_REORDER_CODE_SPACE && code <= UCOL_REORDER_CODE_DIGIT) {
            const char* special[] = {"space", "punct", "symbol", "currency", "digit"};
            name = special[code - UCOL_REORDER_CODE_SPACE];
        } else {
            // ICU77 coll.cpp accepts the Script alias Zzzz for OTHERS and
            // explicitly rejects the English "others" keyword synonym.
            name = uscript_getShortName(static_cast<UScriptCode>(code));
        }
        require(name != nullptr, "Reorder code has no public locale keyword name");
        if (!first) result += '-';
        result += name;
        first = false;
    }
    require(!first, "Expected a nonempty reorder request");
    return result;
}

static std::string raw_key(icu::Collator& collator, const std::vector<char16_t>& text, int strength) {
    collator.setStrength(static_cast<icu::Collator::ECollationStrength>(strength));
    const auto length = collator.getSortKey(text.data(), static_cast<int32_t>(text.size()), nullptr, 0);
    require(length > 0, "Native key preflight failed");
    std::vector<uint8_t> bytes(static_cast<size_t>(length));
    require(collator.getSortKey(text.data(), static_cast<int32_t>(text.size()), bytes.data(), length) == length,
            "Native complete key length changed");
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (auto value : bytes) output << std::setw(2) << static_cast<unsigned>(value);
    return output.str();
}

static std::string boost_key(const std::vector<UChar32>& key) {
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    bool first = true;
    for (auto value : key) {
        if (!first) output << ',';
        output << std::setw(8) << static_cast<uint32_t>(value);
        first = false;
    }
    return output.str();
}

int main() {
    try {
        std::string line;
        require(std::getline(std::cin, line) && line == "case_id\tsetup_codes\trequest_codes\tu16_hex",
                "Invalid reorder scope input header");
        std::cout << "case_id\tlocale\tload_status\treorder_codes\tprimary\tboost_primary\tidentical\tboost_identical\n";
        while (std::getline(std::cin, line)) {
            const auto fields = split(line, '\t');
            require(fields.size() == 4 && !fields[3].empty(), "Scope input requires four nonempty-source fields");
            std::vector<char16_t> text;
            for (const auto& unit : split(fields[3], ',')) text.push_back(static_cast<char16_t>(std::stoul(unit, nullptr, 16)));
            std::vector<UChar32> points;
            for (int32_t index = 0; index < static_cast<int32_t>(text.size());) {
                UChar32 point;
                U16_NEXT(text.data(), index, static_cast<int32_t>(text.size()), point);
                require(point < 0xd800 || point > 0xdfff, "Scope input contains an invalid surrogate");
                points.push_back(point);
            }
            const auto name = locale_name(fields[2]);
            const icu::Locale locale(name.c_str());
            UErrorCode status = U_ZERO_ERROR;
            std::unique_ptr<icu::Collator> native(icu::Collator::createInstance(locale, status));
            require(native && U_SUCCESS(status), "Public locale creation failed");
            const auto load_status = status;
            int32_t codes[256];
            const auto count = native->getReorderCodes(codes, 256, status);
            require(U_SUCCESS(status), "Public reorder code query failed");
            boost::icu_regex_traits traits;
            traits.imbue(locale);
            std::cout << fields[0] << '\t' << name << '\t' << u_errorName(load_status) << '\t';
            for (int32_t i = 0; i < count; ++i) std::cout << (i == 0 ? "" : ",") << codes[i];
            std::cout << '\t' << raw_key(*native, text, UCOL_PRIMARY)
                      << '\t' << boost_key(traits.transform_primary(points.data(), points.data() + points.size()))
                      << '\t' << raw_key(*native, text, UCOL_IDENTICAL)
                      << '\t' << boost_key(traits.transform(points.data(), points.data() + points.size()))
                      << '\n' << std::flush;
        }
        require(!std::cin.bad() && std::cout.good(), "Reorder scope stream failed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "boost-reorder-keys: " << error.what() << '\n';
        return 1;
    }
}
