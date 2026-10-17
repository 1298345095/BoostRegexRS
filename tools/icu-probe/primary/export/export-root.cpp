// Development-only access to ICU4C 77.1's complete root collation tables.
// ICU-derived data/algorithm use: see ../data/LICENSE-ICU.txt and NOTICE.md.
// This executable is never linked into, or executed by, the Rust prototype.

#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "unicode/icudataver.h"
#include "unicode/uchar.h"
#include "unicode/ucharstrie.h"
#include "unicode/ucol.h"
#include "unicode/ulocdata.h"
#include "unicode/uversion.h"
#include "collation.h"
#include "collationdata.h"
#include "collationroot.h"
#include "collationsettings.h"

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This data generator requires official ICU4C 77.1 headers.
#endif

namespace {

using icu::Collation;
using icu::CollationData;
using icu::CollationRoot;
using icu::CollationSettings;
using icu::UCharsTrie;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void check(UErrorCode status, const char* operation) {
    require(U_SUCCESS(status), std::string(operation) + ": " + u_errorName(status));
}

void requireVersion(const UVersionInfo version, uint8_t major, uint8_t minor,
                    const char* name) {
    require(version[0] == major && version[1] == minor && version[2] == 0 &&
                version[3] == 0,
            std::string("unexpected ") + name + " version");
}

class Writer {
public:
    explicit Writer(const char* path) : out_(path, std::ios::binary) {
        require(out_.good(), std::string("cannot open ") + path);
    }

    void byte(uint8_t value) { out_.put(static_cast<char>(value)); }

    void u16(uint16_t value) {
        byte(static_cast<uint8_t>(value));
        byte(static_cast<uint8_t>(value >> 8));
    }

    void u32(uint32_t value) {
        u16(static_cast<uint16_t>(value));
        u16(static_cast<uint16_t>(value >> 16));
    }

    void u64(uint64_t value) {
        u32(static_cast<uint32_t>(value));
        u32(static_cast<uint32_t>(value >> 32));
    }

    void count(size_t value) {
        require(value <= UINT32_MAX, "section exceeds u32 element count");
        u32(static_cast<uint32_t>(value));
    }

    void finish() {
        out_.flush();
        require(out_.good(), "writing collation data failed");
    }

private:
    std::ofstream out_;
};

struct Range32 {
    uint32_t end;
    uint32_t value;
};

struct ContextEntry {
    std::u16string key;
    uint32_t ce32;
};

struct Context {
    uint32_t defaultCe32;
    std::vector<ContextEntry> entries;
};

using Contexts = std::map<uint32_t, Context>;

void noteContext(uint32_t ce32, std::set<uint32_t>& pending) {
    if (Collation::hasCE32Tag(ce32, Collation::PREFIX_TAG) ||
        Collation::hasCE32Tag(ce32, Collation::CONTRACTION_TAG)) {
        pending.insert(Collation::indexFromCE32(ce32));
    }
}

Contexts decodeContexts(const CollationData& data,
                        const std::vector<Range32>& ce32Ranges) {
    std::set<uint32_t> pending;
    for (const auto& range : ce32Ranges) {
        noteContext(range.value, pending);
    }
    for (int32_t i = 0; i < data.ce32sLength; ++i) {
        noteContext(data.ce32s[i], pending);
    }
    for (int32_t i = 0; i < CollationData::JAMO_CE32S_LENGTH; ++i) {
        noteContext(data.jamoCE32s[i], pending);
    }

    Contexts result;
    while (!pending.empty()) {
        const uint32_t index = *pending.begin();
        pending.erase(pending.begin());
        if (result.count(index) != 0) {
            continue;
        }
        require(index + 2 < static_cast<uint32_t>(data.contextsLength),
                "context index outside the ICU contexts table");
        Context context{CollationData::readCE32(data.contexts + index), {}};
        noteContext(context.defaultCe32, pending);

        UErrorCode status = U_ZERO_ERROR;
        // maxStringLength=0 exports every complete trie key without truncation.
        UCharsTrie::Iterator iterator(data.contexts + index + 2, 0, status);
        check(status, "construct UCharsTrie iterator");
        while (iterator.next(status)) {
            check(status, "iterate UCharsTrie");
            const auto& key = iterator.getString();
            const auto ce32 = static_cast<uint32_t>(iterator.getValue());
            context.entries.push_back(
                {std::u16string(key.getBuffer(), static_cast<size_t>(key.length())), ce32});
            noteContext(ce32, pending);
        }
        check(status, "finish UCharsTrie iteration");
        require(!context.entries.empty(), "empty ICU context trie");
        result.emplace(index, std::move(context));
    }
    return result;
}

template <typename Lookup>
std::vector<Range32> ranges(Lookup lookup) {
    std::vector<Range32> result;
    uint32_t previous = lookup(0);
    for (uint32_t cp = 1; cp <= 0x10ffff; ++cp) {
        const uint32_t value = lookup(cp);
        if (value != previous) {
            result.push_back({cp - 1, previous});
            previous = value;
        }
    }
    result.push_back({0x10ffff, previous});
    return result;
}

void writeVersion(std::ostream& out, const UVersionInfo version) {
    out << '[' << static_cast<unsigned>(version[0]) << ','
        << static_cast<unsigned>(version[1]) << ','
        << static_cast<unsigned>(version[2]) << ','
        << static_cast<unsigned>(version[3]) << ']';
}

void exportRoot(const char* binaryPath, const char* metadataPath) {
    UErrorCode status = U_ZERO_ERROR;
    UVersionInfo icuVersion, unicodeVersion, cldrVersion, dataVersion, collationVersion;
    u_getVersion(icuVersion);
    u_getUnicodeVersion(unicodeVersion);
    ulocdata_getCLDRVersion(cldrVersion, &status);
    check(status, "get CLDR version");
    u_getDataVersion(dataVersion, &status);
    check(status, "get data version");
    requireVersion(icuVersion, 77, 1, "ICU");
    requireVersion(unicodeVersion, 16, 0, "Unicode");
    requireVersion(cldrVersion, 47, 0, "CLDR");
    requireVersion(dataVersion, 77, 1, "ICU data");

    const CollationData* data = CollationRoot::getData(status);
    const CollationSettings* defaults = CollationRoot::getSettings(status);
    check(status, "load complete root collation");
    require(data != nullptr && defaults != nullptr, "missing root collation");
    require(data->base == nullptr, "root data unexpectedly has a base tailoring");
    require(data->ce32sLength > 0 && data->cesLength > 0 && data->contextsLength > 0,
            "missing complete root collation tables");

    CollationSettings settings(*defaults);
    settings.setStrength(UCOL_PRIMARY, defaults->options, status);
    check(status, "set root PRIMARY strength");
    require(settings.dontCheckFCD(), "root normalization must remain OFF");
    require(!settings.isNumeric(), "root numeric collation must remain OFF");
    require(settings.getAlternateHandling() == UCOL_NON_IGNORABLE,
            "root alternate handling must remain non-ignorable");
    require(!settings.hasReordering(), "unexpected root primary reordering");
    require((settings.options & CollationSettings::CASE_LEVEL) == 0,
            "unexpected root case level");

    std::unique_ptr<UCollator, decltype(&ucol_close)> collator(ucol_open("root", &status),
                                                            ucol_close);
    check(status, "open public root collator");
    require(collator != nullptr, "public root collator is null");
    ucol_setStrength(collator.get(), UCOL_PRIMARY);
    ucol_getVersion(collator.get(), collationVersion);

    const std::array<std::pair<const char*, UColAttribute>, 8> attributeNames{{
        {"strength", UCOL_STRENGTH},
        {"normalization", UCOL_NORMALIZATION_MODE},
        {"numeric", UCOL_NUMERIC_COLLATION},
        {"alternate", UCOL_ALTERNATE_HANDLING},
        {"case_level", UCOL_CASE_LEVEL},
        {"case_first", UCOL_CASE_FIRST},
        {"french_secondary", UCOL_FRENCH_COLLATION},
        {"hiragana_quaternary", UCOL_HIRAGANA_QUATERNARY_MODE},
    }};
    std::array<int32_t, attributeNames.size()> attributeValues{};
    for (size_t i = 0; i < attributeNames.size(); ++i) {
        attributeValues[i] = ucol_getAttribute(collator.get(), attributeNames[i].second, &status);
        check(status, attributeNames[i].first);
    }
    require(attributeValues[0] == UCOL_PRIMARY && attributeValues[1] == UCOL_OFF &&
                attributeValues[2] == UCOL_OFF && attributeValues[3] == UCOL_NON_IGNORABLE &&
                attributeValues[4] == UCOL_OFF,
            "public root attributes do not match exported private settings");
    require(ucol_getReorderCodes(collator.get(), nullptr, 0, &status) == 0,
            "public root has unexpected reordering");
    check(status, "get root reorder codes");

    const auto ce32Ranges = ranges([data](uint32_t cp) { return data->getCE32(cp); });
    const auto fcdRanges = ranges([data](uint32_t cp) { return data->getFCD16(cp); });
    const auto contexts = decodeContexts(*data, ce32Ranges);

    Writer out(binaryPath);
    for (const char byte : std::string("BRSPRI77")) {
        out.byte(static_cast<uint8_t>(byte));
    }
    out.u32(1);
    for (uint32_t version : {77u, 1u, 16u, 0u, 47u, 0u}) {
        out.u32(version);
    }
    out.u32(static_cast<uint32_t>(settings.options));
    out.u32(settings.variableTop);
    out.u32(data->numericPrimary);

    out.count(ce32Ranges.size());
    for (const auto& range : ce32Ranges) {
        out.u32(range.end);
        out.u32(range.value);
    }
    out.count(data->ce32sLength);
    for (int32_t i = 0; i < data->ce32sLength; ++i) {
        out.u32(data->ce32s[i]);
    }
    out.count(data->cesLength);
    for (int32_t i = 0; i < data->cesLength; ++i) {
        out.u64(static_cast<uint64_t>(data->ces[i]));
    }
    out.count(data->contextsLength);
    for (int32_t i = 0; i < data->contextsLength; ++i) {
        out.u16(data->contexts[i]);
    }
    out.count(CollationData::JAMO_CE32S_LENGTH);
    for (int32_t i = 0; i < CollationData::JAMO_CE32S_LENGTH; ++i) {
        out.u32(data->jamoCE32s[i]);
    }
    out.count(256);
    for (int32_t i = 0; i < 256; ++i) {
        out.byte(data->compressibleBytes[i] ? 1 : 0);
    }
    out.count(fcdRanges.size());
    for (const auto& range : fcdRanges) {
        out.u32(range.end);
        out.u16(static_cast<uint16_t>(range.value));
    }
    out.count(contexts.size());
    size_t contextEntryCount = 0;
    for (const auto& [index, context] : contexts) {
        out.u32(index);
        out.u32(context.defaultCe32);
        out.count(context.entries.size());
        for (const auto& entry : context.entries) {
            out.count(entry.key.size());
            for (char16_t unit : entry.key) {
                out.u16(unit);
            }
            out.u32(entry.ce32);
        }
        contextEntryCount += context.entries.size();
    }
    out.finish();

    std::array<uint64_t, 17> codePointTagCounts{};
    uint32_t start = 0;
    for (const auto& range : ce32Ranges) {
        const int tag = Collation::isSpecialCE32(range.value)
                            ? Collation::tagFromCE32(range.value)
                            : 16;
        codePointTagCounts[tag] += range.end - start + 1;
        start = range.end + 1;
    }

    std::ofstream metadata(metadataPath);
    require(metadata.good(), "cannot create root metadata");
    metadata << "{\n  \"schema\": 1,\n  \"icu\": ";
    writeVersion(metadata, icuVersion);
    metadata << ",\n  \"unicode\": ";
    writeVersion(metadata, unicodeVersion);
    metadata << ",\n  \"cldr\": ";
    writeVersion(metadata, cldrVersion);
    metadata << ",\n  \"icu_data\": ";
    writeVersion(metadata, dataVersion);
    metadata << ",\n  \"collation_version\": ";
    writeVersion(metadata, collationVersion);
    metadata << ",\n  \"requested_locale\": \"root\",\n  \"valid_locale\": \""
             << ucol_getLocaleByType(collator.get(), ULOC_VALID_LOCALE, &status)
             << "\",\n  \"actual_locale\": \""
             << ucol_getLocaleByType(collator.get(), ULOC_ACTUAL_LOCALE, &status)
             << "\",\n  \"root_has_base\": false,\n  \"primary_options\": " << settings.options
             << ",\n  \"variable_top\": " << settings.variableTop
             << ",\n  \"numeric_primary\": " << data->numericPrimary
             << ",\n  \"reordering\": [],\n  \"attributes\": {";
    check(status, "get root locale identity");
    for (size_t i = 0; i < attributeNames.size(); ++i) {
        metadata << (i == 0 ? "\n" : ",\n") << "    \"" << attributeNames[i].first
                 << "\": " << attributeValues[i];
    }
    metadata << "\n  },\n  \"counts\": {\n    \"ce32_ranges\": " << ce32Ranges.size()
             << ",\n    \"ce32s\": " << data->ce32sLength
             << ",\n    \"ces\": " << data->cesLength
             << ",\n    \"raw_context_units\": " << data->contextsLength
             << ",\n    \"jamo_ce32s\": " << CollationData::JAMO_CE32S_LENGTH
             << ",\n    \"compressible_bytes\": 256"
             << ",\n    \"fcd16_ranges\": " << fcdRanges.size()
             << ",\n    \"decoded_contexts\": " << contexts.size()
             << ",\n    \"decoded_context_entries\": " << contextEntryCount
             << "\n  },\n  \"codepoint_ce32_tag_counts\": {";
    for (size_t i = 0; i < codePointTagCounts.size(); ++i) {
        metadata << (i == 0 ? "\n" : ",\n") << "    \""
                 << (i == 16 ? "simple" : std::to_string(i)) << "\": " << codePointTagCounts[i];
    }
    metadata << "\n  }\n}\n";
    metadata.flush();
    require(metadata.good(), "writing root metadata failed");
    std::cout << "exported " << ce32Ranges.size() << " CE32 ranges, " << contexts.size()
              << " context tries, " << contextEntryCount << " context entries\n";
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: export-root DATA.bin METADATA.json\n";
        return 2;
    }
    try {
        exportRoot(argv[1], argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "export-root: " << error.what() << '\n';
        return 1;
    }
}
