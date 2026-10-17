// Test-only expected values for the approved empty-input compatibility exception.
// Uses the external ICU 77.1 reference; no production Rust implementation implied.
#include <unicode/coll.h>
#include <unicode/uchar.h>
#include <unicode/ulocdata.h>
#include <unicode/icudataver.h>
#include <unicode/uversion.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>

std::string version(const UVersionInfo value) {
    char buffer[U_MAX_VERSION_STRING_LENGTH];
    u_versionToString(value, buffer);
    return buffer;
}

std::string compiler_identity() {
#if defined(_MSC_VER)
    return "MSVC " + std::to_string(_MSC_VER);
#elif defined(__clang__)
    return "Clang " __clang_version__;
#elif defined(__GNUC__)
    return "GCC " __VERSION__;
#else
    return "unknown C++ compiler";
#endif
}

std::string hex(const std::vector<std::uint8_t>& bytes, int width) {
    std::ostringstream stream;
    bool first = true;
    for (auto byte : bytes) {
        if (!first) stream << ',';
        first = false;
        stream << std::hex << std::setfill('0') << std::setw(width)
               << static_cast<unsigned>(byte);
    }
    return stream.str();
}

int main(int argc, char** argv) try {
    if (argc != 2) throw std::runtime_error("usage: empty-keys OUTPUT_DIRECTORY");
    const std::filesystem::path directory(argv[1]);
    std::filesystem::create_directories(directory);
    UErrorCode status = U_ZERO_ERROR;
    UVersionInfo icu{}, unicode{}, cldr{}, data{};
    u_getVersion(icu);
    u_getUnicodeVersion(unicode);
    ulocdata_getCLDRVersion(cldr, &status);
    u_getDataVersion(data, &status);
    if (U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
    if (icu[0] != 77 || icu[1] != 1 || unicode[0] != 16 || unicode[1] != 0 || cldr[0] != 47 || data[0] != 77 || data[1] != 1)
        throw std::runtime_error("Unexpected reference version");

    std::ofstream metadata(directory / "metadata.json");
    metadata << "{\n  \"purpose\": \"expected values for approved empty-input compatibility exception\",\n"
             << "  \"icu\": \"" << version(icu) << "\",\n"
             << "  \"unicode\": \"" << version(unicode) << "\",\n"
             << "  \"cldr\": \"" << version(cldr) << "\",\n"
             << "  \"data\": \"" << version(data) << "\",\n"
             << "  \"compiler\": \"" << compiler_identity() << "\",\n"
             << "  \"valid_sentinel_pointer\": true,\n  \"input_utf16_units\": 0,\n"
             << "  \"locale_count\": 10,\n  \"key_count\": 20,\n"
             << "  \"rust_full_key_implementation_verified\": false\n}\n";

    std::ofstream output(directory / "keys.tsv");
    output << "locale\tstrength\ticu_raw_bytes\tboost_u32_key\n";
    std::ofstream settings(directory / "collator-settings.tsv");
    settings << "locale\tstrength\trequested_locale\tvalid_locale\tactual_locale\tnormalization_mode\tnormalization_raw\n";
    for (const auto name : {"root", "en_US", "tr_TR", "de_DE", "sv_SE", "fr_CA", "es_ES@collation=traditional", "zh_CN", "ja_JP", "th_TH"}) {
        const auto locale = std::string(name) == "root" ? icu::Locale::getRoot() : icu::Locale::createFromName(name);
        for (const auto strength : {icu::Collator::PRIMARY, icu::Collator::IDENTICAL}) {
            status = U_ZERO_ERROR;
            std::unique_ptr<icu::Collator> collator(icu::Collator::createInstance(locale, status));
            if (U_FAILURE(status) || !collator) throw std::runtime_error("Collator creation failed");
            collator->setStrength(strength);
            // Inspect the constructed collator, rather than assuming the ICU
            // constructor default. getAttribute is stable since ICU 2.2;
            // getLocale and ULOC_VALID/ACTUAL_LOCALE are declared by ICU 77.1.
            status = U_ZERO_ERROR;
            const auto normalization = collator->getAttribute(UCOL_NORMALIZATION_MODE, status);
            if (U_FAILURE(status)) throw std::runtime_error("Normalization query failed");
            status = U_ZERO_ERROR;
            const auto valid = collator->getLocale(ULOC_VALID_LOCALE, status);
            if (U_FAILURE(status)) throw std::runtime_error("Valid locale query failed");
            status = U_ZERO_ERROR;
            const auto actualLocale = collator->getLocale(ULOC_ACTUAL_LOCALE, status);
            if (U_FAILURE(status)) throw std::runtime_error("Actual locale query failed");
            const char* normalizationName = normalization == UCOL_ON ? "UCOL_ON"
                                        : normalization == UCOL_OFF ? "UCOL_OFF" : "OTHER";
            settings << name << '\t' << (strength == icu::Collator::PRIMARY ? "PRIMARY" : "IDENTICAL")
                     << '\t' << locale.getName() << '\t' << valid.getName() << '\t' << actualLocale.getName()
                     << '\t' << normalizationName << '\t' << static_cast<int>(normalization) << '\n';
            const UChar sentinel = 0;
            const auto length = collator->getSortKey(&sentinel, 0, nullptr, 0);
            if (length <= 0) throw std::runtime_error("Empty sort-key preflight failed");
            std::vector<std::uint8_t> raw(static_cast<std::size_t>(length));
            const auto actual = collator->getSortKey(&sentinel, 0, raw.data(), length);
            if (actual != length) throw std::runtime_error("Empty sort-key length changed");
            auto wrapped = raw;
            // Boost 1.89.0 icu_regex_traits_implementation::do_transform strips
            // one terminator only when len > 1, then promotes each byte to u32.
            if (wrapped.size() > 1 && wrapped.back() == 0) wrapped.pop_back();
            output << name << '\t' << (strength == icu::Collator::PRIMARY ? "PRIMARY" : "IDENTICAL")
                   << '\t' << hex(raw, 2) << '\t' << hex(wrapped, 8) << '\n';
        }
    }
    if (!output || !metadata || !settings) throw std::runtime_error("Output write failed");
    std::cout << "ICU " << version(icu) << ", Unicode " << version(unicode)
              << ", CLDR " << version(cldr) << "; exported 20 empty-key expectations\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
