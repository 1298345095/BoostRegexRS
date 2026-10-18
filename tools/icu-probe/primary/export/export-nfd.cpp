// Development-only fixed Unicode 16 canonical decomposition and CCC export.
// ICU source/data: ../data/LICENSE-ICU.txt and ../data/NOTICE.md.
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <unicode/icudataver.h>
#include <unicode/normalizer2.h>
#include <unicode/ulocdata.h>
#include <unicode/utf16.h>
#include <unicode/uversion.h>
#include "collationroot.h"
#include "collationsettings.h"

namespace {
void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
void version(const UVersionInfo value, unsigned major, unsigned minor) {
    require(value[0] == major && value[1] == minor && value[2] == 0 && value[3] == 0,
            "Unexpected ICU/Unicode/CLDR/data version");
}
class Writer {
public:
    explicit Writer(const char* path) : out(path, std::ios::binary) {
        require(out.good(), "Cannot open NFD output");
    }
    void byte(uint8_t value) { out.put(static_cast<char>(value)); }
    void word(uint32_t value) {
        for (unsigned shift = 0; shift < 32; shift += 8) byte(static_cast<uint8_t>(value >> shift));
    }
    void finish() { out.flush(); require(out.good(), "NFD output write failed"); }
private:
    std::ofstream out;
};
struct Mapping { uint32_t cp; std::vector<uint32_t> decomposition; };
struct Range { uint32_t end; uint8_t ccc; };
}

int main(int argc, char** argv) try {
    require(argc == 3, "usage: export-nfd DATA.bin METADATA.json");
    UErrorCode status = U_ZERO_ERROR;
    UVersionInfo icu{}, unicode{}, cldr{}, data{};
    u_getVersion(icu); u_getUnicodeVersion(unicode);
    ulocdata_getCLDRVersion(cldr, &status); u_getDataVersion(data, &status);
    require(U_SUCCESS(status), "Version lookup failed");
    version(icu, 77, 1); version(unicode, 16, 0); version(cldr, 47, 0); version(data, 77, 1);
    const auto* defaults = icu::CollationRoot::getSettings(status);
    require(U_SUCCESS(status) && defaults != nullptr, "Root settings load failed");
    icu::CollationSettings identical(*defaults);
    identical.setStrength(UCOL_IDENTICAL, defaults->options, status);
    require(U_SUCCESS(status) && identical.options == 0xf010 && !identical.hasReordering(),
            "Unexpected root IDENTICAL options");
    const auto* nfd = icu::Normalizer2::getNFDInstance(status);
    require(U_SUCCESS(status) && nfd != nullptr, "NFD data load failed");
    std::vector<Mapping> mappings;
    std::vector<Range> ranges;
    uint8_t previous = nfd->getCombiningClass(0);
    uint32_t mappingScalars = 0;
    uint32_t maximumLength = 0;
    for (uint32_t cp = 0; cp <= 0x10ffff; ++cp) {
        const uint8_t ccc = nfd->getCombiningClass(cp);
        if (ccc != previous) { ranges.push_back({cp - 1, previous}); previous = ccc; }
        icu::UnicodeString text;
        // getDecomposition returns the processed, recursively decomposed mapping.
        if (nfd->getDecomposition(cp, text)) {
            Mapping mapping{cp, {}};
            for (int32_t i = 0; i < text.length();) {
                const auto scalar = text.char32At(i);
                require(scalar >= 0 && scalar <= 0x10ffff && !U_IS_SURROGATE(scalar),
                        "Non-scalar canonical decomposition");
                mapping.decomposition.push_back(static_cast<uint32_t>(scalar));
                i += U16_LENGTH(scalar);
            }
            require(!mapping.decomposition.empty(), "Empty canonical decomposition");
            mappingScalars += static_cast<uint32_t>(mapping.decomposition.size());
            if (mapping.decomposition.size() > maximumLength)
                maximumLength = static_cast<uint32_t>(mapping.decomposition.size());
            mappings.push_back(std::move(mapping));
        }
    }
    ranges.push_back({0x10ffff, previous});
    Writer out(argv[1]);
    for (const char byte : std::string("BRSNFD77")) out.byte(static_cast<uint8_t>(byte));
    out.word(1);
    for (uint32_t value : {77u, 1u, 16u, 0u, 47u, 0u}) out.word(value);
    out.word(static_cast<uint32_t>(mappings.size()));
    for (const auto& mapping : mappings) {
        out.word(mapping.cp); out.word(static_cast<uint32_t>(mapping.decomposition.size()));
        for (uint32_t cp : mapping.decomposition) out.word(cp);
    }
    out.word(static_cast<uint32_t>(ranges.size()));
    for (const auto& range : ranges) { out.word(range.end); out.byte(range.ccc); }
    out.finish();
    std::ofstream metadata(argv[2]);
    metadata << "{\n  \"icu\": \"77.1\",\n  \"unicode\": \"16.0.0\",\n"
             << "  \"cldr\": \"47.0\",\n  \"icu_data\": \"77.1\",\n"
             << "  \"normalization\": \"NFD, canonical only, recursively decomposed\",\n"
             << "  \"hangul_included\": true,\n  \"mapping_count\": " << mappings.size()
             << ",\n  \"root_identical_options\": " << identical.options
             << ",\n  \"mapping_scalars\": " << mappingScalars
             << ",\n  \"maximum_mapping_length\": " << maximumLength
             << ",\n  \"ccc_ranges\": " << ranges.size() << "\n}\n";
    metadata.flush(); require(metadata.good(), "NFD metadata write failed");
    std::cout << "exported " << mappings.size() << " recursive canonical mappings and "
              << ranges.size() << " CCC ranges\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
