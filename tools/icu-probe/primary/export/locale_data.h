// Development-only serialization of the actual ICU4C 77.1 data/settings.
// ICU-derived context traversal: ../data/NOTICE.md and ../data/LICENSE-ICU.txt.
#ifndef BOOSTREGEXRS_LOCALE_DATA_H
#define BOOSTREGEXRS_LOCALE_DATA_H

#include <cstdint>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <unicode/ucharstrie.h>
#include "collation.h"
#include "collationdata.h"
#include "collationsettings.h"

namespace export77 {
inline void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

class Writer {
public:
    explicit Writer(const std::string& path) : out_(path, std::ios::binary) {
        require(out_.good(), "Cannot create locale data output");
    }
    void byte(uint8_t value) { out_.put(static_cast<char>(value)); }
    void u16(uint16_t value) { byte(value); byte(value >> 8); }
    void u32(uint32_t value) { u16(value); u16(value >> 16); }
    void u64(uint64_t value) { u32(value); u32(value >> 32); }
    void count(size_t value) {
        require(value <= UINT32_MAX, "Locale section count exceeds u32");
        u32(static_cast<uint32_t>(value));
    }
    void header(const char* magic) {
        for (size_t i = 0; i < 8; ++i) byte(magic[i]);
        u32(1);
        for (uint32_t value : {77u, 1u, 16u, 0u, 47u, 0u}) u32(value);
    }
    void finish() { out_.flush(); require(out_.good(), "Locale data write failed"); }
private:
    std::ofstream out_;
};

struct Range { uint32_t end; uint32_t ce32; };
struct Entry { std::u16string key; uint32_t ce32; };
struct Context { uint32_t default_ce32; std::vector<Entry> entries; };

inline std::vector<Range> ranges(const icu::CollationData& data) {
    std::vector<Range> values;
    uint32_t previous = data.getCE32(0);
    for (uint32_t cp = 1; cp <= 0x10ffff; ++cp) {
        const uint32_t current = data.getCE32(cp);
        if (current != previous) { values.push_back({cp - 1, previous}); previous = current; }
    }
    values.push_back({0x10ffff, previous});
    return values;
}

inline void note_context(uint32_t ce32, std::set<uint32_t>& pending) {
    if (icu::Collation::hasCE32Tag(ce32, icu::Collation::PREFIX_TAG) ||
        icu::Collation::hasCE32Tag(ce32, icu::Collation::CONTRACTION_TAG)) {
        pending.insert(icu::Collation::indexFromCE32(ce32));
    }
}

inline std::map<uint32_t, Context> contexts(const icu::CollationData& data,
                                          const std::vector<Range>& values) {
    std::set<uint32_t> pending;
    for (const auto& item : values) note_context(item.ce32, pending);
    for (int32_t i = 0; i < data.ce32sLength; ++i) note_context(data.ce32s[i], pending);
    for (int32_t i = 0; i < icu::CollationData::JAMO_CE32S_LENGTH; ++i) note_context(data.jamoCE32s[i], pending);
    std::map<uint32_t, Context> result;
    while (!pending.empty()) {
        const auto index = *pending.begin(); pending.erase(pending.begin());
        if (result.count(index)) continue;
        require(index + 2 < static_cast<uint32_t>(data.contextsLength), "Owner context index outside raw table");
        Context context{icu::CollationData::readCE32(data.contexts + index), {}};
        note_context(context.default_ce32, pending);
        UErrorCode status = U_ZERO_ERROR;
        // A zero limit enumerates complete keys, including arbitrarily long ones.
        icu::UCharsTrie::Iterator iterator(data.contexts + index + 2, 0, status);
        require(U_SUCCESS(status), "Owner context iterator creation failed");
        while (iterator.next(status)) {
            require(U_SUCCESS(status), "Owner context iterator failed");
            const auto& key = iterator.getString();
            const auto ce32 = static_cast<uint32_t>(iterator.getValue());
            context.entries.push_back({std::u16string(key.getBuffer(), static_cast<size_t>(key.length())), ce32});
            note_context(ce32, pending);
        }
        require(U_SUCCESS(status), "Owner context iteration did not complete");
        require(!context.entries.empty(), "Empty referenced owner context trie");
        result.emplace(index, std::move(context));
    }
    return result;
}

inline void write_owner(const std::string& path, const icu::CollationData& data) {
    const auto values = ranges(data);
    const auto decoded = contexts(data, values);
    Writer out(path); out.header("BRSOWN77"); out.u32(data.numericPrimary);
    out.count(values.size());
    for (const auto& value : values) { out.u32(value.end); out.u32(value.ce32); }
    out.count(data.ce32sLength);
    for (int32_t i = 0; i < data.ce32sLength; ++i) out.u32(data.ce32s[i]);
    out.count(data.cesLength);
    for (int32_t i = 0; i < data.cesLength; ++i) out.u64(data.ces[i]);
    out.count(data.contextsLength);
    for (int32_t i = 0; i < data.contextsLength; ++i) out.u16(data.contexts[i]);
    out.count(icu::CollationData::JAMO_CE32S_LENGTH);
    for (int32_t i = 0; i < icu::CollationData::JAMO_CE32S_LENGTH; ++i) out.u32(data.jamoCE32s[i]);
    out.count(256);
    for (int32_t i = 0; i < 256; ++i) out.byte(data.compressibleBytes[i] ? 1 : 0);
    out.count(decoded.size());
    for (const auto& item : decoded) {
        out.u32(item.first); out.u32(item.second.default_ce32); out.count(item.second.entries.size());
        for (const auto& entry : item.second.entries) {
            out.count(entry.key.size());
            for (auto unit : entry.key) out.u16(unit);
            out.u32(entry.ce32);
        }
    }
    out.finish();
}

inline void write_settings(const std::string& path, const icu::CollationSettings& settings) {
    Writer out(path); out.header("BRSSET77"); out.u32(settings.options); out.u32(settings.variableTop);
    out.count(settings.reorderCodesLength);
    for (int32_t i = 0; i < settings.reorderCodesLength; ++i) out.u32(static_cast<uint32_t>(settings.reorderCodes[i]));
    out.count(settings.reorderTable ? 256 : 0);
    if (settings.reorderTable) for (int32_t i = 0; i < 256; ++i) out.byte(settings.reorderTable[i]);
    out.u32(settings.minHighNoReorder); out.count(settings.reorderRangesLength);
    for (int32_t i = 0; i < settings.reorderRangesLength; ++i) out.u32(settings.reorderRanges[i]);
    out.finish();
}

inline void write_scripts(const std::string& path, const icu::CollationData& data) {
    Writer out(path); out.header("BRSSCR77"); out.u32(data.numScripts);
    out.count(data.numScripts + 16);
    for (int32_t i = 0; i < data.numScripts + 16; ++i) out.u16(data.scriptsIndex[i]);
    out.count(data.scriptStartsLength);
    for (int32_t i = 0; i < data.scriptStartsLength; ++i) out.u16(data.scriptStarts[i]);
    out.finish();
}
}  // namespace export77
#endif
