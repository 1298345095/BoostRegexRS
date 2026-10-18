// Development-only inventory of the complete, fixed ICU4C 77.1 collation data.
// ICU source/data attribution: ../data/NOTICE.md and ../data/LICENSE-ICU.txt.
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <unicode/coll.h>
#include <unicode/icudataver.h>
#include <unicode/strenum.h>
#include <unicode/ulocdata.h>
#include <unicode/uversion.h>
#include "collation.h"
#include "collationdata.h"
#include "collationroot.h"
#include "collationsettings.h"
#include "collationtailoring.h"
#include "ucol_imp.h"
#include "locale_data.h"
#include "locale_resources.h"

namespace {
using icu::Collation;
using icu::CollationCacheEntry;
using icu::CollationData;
using icu::CollationSettings;

void require(bool value, const std::string& reason) {
    if (!value) throw std::runtime_error(reason);
}
void check(UErrorCode status, const char* action) {
    require(U_SUCCESS(status), std::string(action) + ": " + u_errorName(status));
}
std::string quote(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (const unsigned char ch : value) {
        if (ch == '"' || ch == '\\') out << '\\' << ch;
        else if (ch < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(ch);
        else out << ch;
    }
    out << '"';
    return out.str();
}
template <typename T> void numbers(std::ostream& out, const T* values, size_t count) {
    out << '[';
    for (size_t i = 0; i < count; ++i) out << (i ? "," : "") << +values[i];
    out << ']';
}
void strings(std::ostream& out, const std::vector<std::string>& values) {
    out << '[';
    for (size_t i = 0; i < values.size(); ++i) out << (i ? "," : "") << quote(values[i]);
    out << ']';
}
std::vector<std::string> lines(const char* path) {
    std::ifstream input(path);
    require(input.good(), "Cannot open locale enumeration input");
    std::vector<std::string> values;
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (!line.empty()) values.push_back(line);
    }
    require(input.eof(), "Locale enumeration input read failed");
    return values;
}
std::string filename(const char* prefix, size_t index) {
    std::ostringstream name;
    name << prefix << '-' << std::setfill('0') << std::setw(4) << index << ".bin";
    return name.str();
}
std::vector<std::string> enumeration(icu::StringEnumeration* raw, UErrorCode& status) {
    std::unique_ptr<icu::StringEnumeration> values(raw);
    check(status, "create enumeration");
    require(values != nullptr, "null enumeration");
    std::vector<std::string> result;
    while (const char* value = values->next(nullptr, status)) result.emplace_back(value);
    check(status, "enumerate values");
    return result;
}
void version(const UVersionInfo value, int major, int minor) {
    require(value[0] == major && value[1] == minor && value[2] == 0 && value[3] == 0,
            "Unexpected ICU/Unicode/CLDR/data version");
}
void versions() {
    UVersionInfo runtime{}, unicode{}, cldr{}, data{};
    UErrorCode status = U_ZERO_ERROR;
    u_getVersion(runtime); u_getUnicodeVersion(unicode);
    ulocdata_getCLDRVersion(cldr, &status); u_getDataVersion(data, &status);
    check(status, "get fixed versions");
    version(runtime, 77, 1); version(unicode, 16, 0); version(cldr, 47, 0); version(data, 77, 1);
}

const std::array<std::pair<const char*, UColAttribute>, 7> ATTRIBUTES{{
    {"strength", UCOL_STRENGTH}, {"normalization", UCOL_NORMALIZATION_MODE},
    {"numeric", UCOL_NUMERIC_COLLATION}, {"alternate", UCOL_ALTERNATE_HANDLING},
    {"case_level", UCOL_CASE_LEVEL}, {"case_first", UCOL_CASE_FIRST},
    {"french_secondary", UCOL_FRENCH_COLLATION},
}};

std::string settings_json(const CollationSettings& settings, const icu::Collator& collator) {
    const std::array<int32_t, 7> expected{{
        settings.getStrength(), settings.getFlag(CollationSettings::CHECK_FCD),
        settings.getFlag(CollationSettings::NUMERIC), settings.getAlternateHandling(),
        settings.getFlag(CollationSettings::CASE_LEVEL), settings.getCaseFirst(),
        settings.getFlag(CollationSettings::BACKWARD_SECONDARY),
    }};
    UErrorCode status = U_ZERO_ERROR;
    std::ostringstream out;
    out << "{\"options\":" << settings.options << ",\"variable_top\":" << settings.variableTop
        << ",\"attributes\":{";
    for (size_t i = 0; i < ATTRIBUTES.size(); ++i) {
        const int32_t actual = collator.getAttribute(ATTRIBUTES[i].second, status);
        check(status, ATTRIBUTES[i].first);
        require(actual == expected[i], std::string("Public/private attribute mismatch: ") + ATTRIBUTES[i].first);
        out << (i ? "," : "") << quote(ATTRIBUTES[i].first) << ':' << actual;
    }
    require(collator.getVariableTop(status) == settings.variableTop, "Public/private variableTop mismatch");
    require(collator.getMaxVariable() == UCOL_REORDER_CODE_FIRST + int32_t(settings.getMaxVariable()),
            "Public/private maxVariable mismatch");
    int32_t count = collator.getReorderCodes(nullptr, 0, status);
    require(status == U_BUFFER_OVERFLOW_ERROR || U_SUCCESS(status), "Reorder preflight failed");
    status = U_ZERO_ERROR;
    std::vector<int32_t> codes(static_cast<size_t>(count));
    require(collator.getReorderCodes(codes.data(), count, status) == count, "Reorder preflight changed");
    check(status, "get public reordering");
    require(count == settings.reorderCodesLength, "Public/private reorder count mismatch");
    for (int32_t i = 0; i < count; ++i) require(codes[i] == settings.reorderCodes[i], "Public/private reorder code mismatch");
    out << "},\"reorder_codes\":";
    numbers(out, settings.reorderCodes, settings.reorderCodesLength);
    out << ",\"reorder_table\":";
    if (settings.reorderTable) numbers(out, settings.reorderTable, 256);
    else out << "null";
    out << ",\"min_high_no_reorder\":" << settings.minHighNoReorder << ",\"reorder_ranges\":";
    numbers(out, settings.reorderRanges, settings.reorderRangesLength);
    out << '}';
    return out.str();
}

std::unique_ptr<CollationSettings> effective_settings(const CollationSettings& defaults,
                                                     const CollationData& data,
                                                     const icu::Collator& collator) {
    // Public createInstance() applies locale attribute keywords after loading the
    // tailoring. Use the same official setters, without exposing private layout.
    auto result = std::make_unique<CollationSettings>(defaults);
    UErrorCode status = U_ZERO_ERROR;
    result->setStrength(collator.getAttribute(UCOL_STRENGTH, status), defaults.options, status);
    for (const auto& attribute : std::array<std::pair<UColAttribute, int32_t>, 4>{{
             {UCOL_NORMALIZATION_MODE, CollationSettings::CHECK_FCD},
             {UCOL_NUMERIC_COLLATION, CollationSettings::NUMERIC},
             {UCOL_CASE_LEVEL, CollationSettings::CASE_LEVEL},
             {UCOL_FRENCH_COLLATION, CollationSettings::BACKWARD_SECONDARY}}}) {
        result->setFlag(attribute.second, collator.getAttribute(attribute.first, status), defaults.options, status);
    }
    result->setAlternateHandling(collator.getAttribute(UCOL_ALTERNATE_HANDLING, status), defaults.options, status);
    result->setCaseFirst(collator.getAttribute(UCOL_CASE_FIRST, status), defaults.options, status);
    result->setMaxVariable(collator.getMaxVariable() - UCOL_REORDER_CODE_FIRST, defaults.options, status);
    result->variableTop = collator.getVariableTop(status);
    check(status, "export effective public attributes with official settings setters");
    int32_t count = collator.getReorderCodes(nullptr, 0, status);
    require(status == U_BUFFER_OVERFLOW_ERROR || U_SUCCESS(status), "Effective reordering preflight failed");
    status = U_ZERO_ERROR;
    std::vector<int32_t> codes(static_cast<size_t>(count));
    require(collator.getReorderCodes(codes.data(), count, status) == count, "Effective reorder count changed");
    check(status, "read effective reorder codes");
    bool changed = count != defaults.reorderCodesLength;
    for (int32_t i = 0; i < count && !changed; ++i) changed = codes[i] != defaults.reorderCodes[i];
    if (changed) result->setReordering(data, codes.data(), count, status);
    check(status, "export effective official ICU reordering");
    return result;
}

struct Release { void operator()(const CollationCacheEntry* entry) const { entry->removeRef(); } };
struct Registry {
    std::map<const CollationData*, size_t> identifiers;
    std::vector<const CollationData*> owners;
    std::vector<std::unique_ptr<const CollationCacheEntry, Release>> retained;
    std::map<std::string, size_t> settings_identifiers;
    std::vector<std::string> settings;
    std::vector<std::unique_ptr<CollationSettings>> settings_data;
    size_t owner(const CollationData* data) {
        auto found = identifiers.find(data);
        if (found != identifiers.end()) return found->second;
        if (data->base) owner(data->base);
        const size_t id = owners.size();
        identifiers.emplace(data, id); owners.push_back(data);
        return id;
    }
    size_t setting(const std::string& value, std::unique_ptr<CollationSettings> data) {
        auto found = settings_identifiers.find(value);
        if (found != settings_identifiers.end()) return found->second;
        const size_t id = settings.size();
        settings_identifiers.emplace(value, id); settings.push_back(value); settings_data.push_back(std::move(data));
        return id;
    }
};

std::string request_json(const std::string& requested, Registry& registry) {
    const icu::Locale locale = icu::Locale::createFromName(requested.c_str());
    UErrorCode status = U_ZERO_ERROR;
    const auto* entry = icu::CollationLoader::loadTailoring(locale, status);
    const auto load_status = status;
    if (entry) registry.retained.emplace_back(entry);
    status = U_ZERO_ERROR;
    std::unique_ptr<icu::Collator> collator(icu::Collator::createInstance(locale, status));
    const auto public_status = status;
    std::ostringstream out;
    out << "{\"requested\":" << quote(requested) << ",\"normalized\":" << quote(locale.getName())
        << ",\"load_status\":" << quote(u_errorName(load_status))
        << ",\"public_status\":" << quote(u_errorName(public_status));
    if (U_FAILURE(load_status) || U_FAILURE(public_status)) {
        require(U_FAILURE(load_status) == !bool(entry) && U_FAILURE(public_status) == !bool(collator),
                "Native locale creation returned inconsistent status/object");
        out << ",\"status\":\"reference_rejected\",\"owner\":null,\"settings\":null}";
        return out.str();
    }
    require(entry != nullptr && collator != nullptr, "Missing successful native locale object");
    const size_t owner = registry.owner(entry->tailoring->data);
    const std::string normalized(locale.getName());
    const auto at = normalized.find('@');
    const bool default_attributes = at == std::string::npos ||
        (normalized.compare(at + 1, 10, "collation=") == 0 && normalized.find(';', at) == std::string::npos);
    if (default_attributes) settings_json(*entry->tailoring->settings, *collator);
    auto effective = effective_settings(*entry->tailoring->settings, *entry->tailoring->data, *collator);
    const auto setting_json = settings_json(*effective, *collator);
    const size_t setting = registry.setting(setting_json, std::move(effective));
    status = U_ZERO_ERROR;
    const auto valid = collator->getLocale(ULOC_VALID_LOCALE, status);
    const auto actual = collator->getLocale(ULOC_ACTUAL_LOCALE, status);
    check(status, "get public locale identity");
    require(valid == entry->validLocale && actual == entry->tailoring->actualLocale,
            "Public/private locale identity mismatch");
    out << ",\"status\":\"loaded\",\"valid\":" << quote(valid.getName()) << ",\"actual\":" << quote(actual.getName())
        << ",\"default_attributes\":" << (default_attributes ? "true" : "false")
        << ",\"owner\":" << owner << ",\"settings\":" << setting << ",\"tailoring_version\":";
    numbers(out, entry->tailoring->version, 4);
    out << '}';
    return out.str();
}

void add_type(std::set<std::string>& requests, const icu::Locale& locale, const std::string& type) {
    auto typed = locale;
    UErrorCode status = U_ZERO_ERROR;
    typed.setKeywordValue("collation", type.c_str(), status);
    check(status, "set inventoried collation type");
    requests.insert(typed.getName());
}

std::string resource_json(const export77::ResourceInfo& resource) {
    std::ostringstream out;
    out << "{\"locale\":" << quote(resource.name) << ",\"bundle_alias\":" << quote(resource.alias)
        << ",\"explicit_parent\":" << quote(resource.parent)
        << ",\"parent_is_root\":" << (resource.parent_is_root ? "true" : "false")
        << ",\"no_fallback\":" << (resource.no_fallback ? "true" : "false")
        << ",\"collations_alias\":" << quote(resource.collations_alias) << ",\"keys\":";
    strings(out, resource.keys); out << ",\"types\":[";
    for (size_t i = 0; i < resource.types.size(); ++i) {
        const auto& type = resource.types[i];
        out << (i ? "," : "") << "{\"name\":" << quote(type.name) << ",\"resource_type\":" << type.resource_type
            << ",\"alias\":" << quote(type.alias) << ",\"string_value\":" << quote(type.string_value)
            << ",\"has_binary\":" << (type.has_binary ? "true" : "false") << ",\"binary_bytes\":" << type.binary_bytes
            << ",\"keys\":";
        strings(out, type.keys); out << '}';
    }
    out << "]}";
    return out.str();
}

void export_data(const std::filesystem::path& directory, const Registry& registry) {
    std::filesystem::create_directories(directory);
    // Export root once for byte-for-byte comparison with the previously frozen
    // root tables. The final catalog reuses root-icu77.bin instead of duplicating it.
    for (size_t i = 0; i < registry.owners.size(); ++i)
        export77::write_owner((directory / filename("owner", i)).string(), *registry.owners[i]);
    for (size_t i = 0; i < registry.settings_data.size(); ++i)
        export77::write_settings((directory / filename("settings", i)).string(), *registry.settings_data[i]);
    const auto& root = *registry.owners.front();
    for (const auto* owner : registry.owners) {
        require(owner->numScripts == root.numScripts && owner->scriptStartsLength == root.scriptStartsLength,
                "Fixed ICU data requires more than one script metadata owner");
        for (int32_t i = 0; i < root.numScripts + 16; ++i)
            require(owner->scriptsIndex[i] == root.scriptsIndex[i], "Fixed ICU script indexes unexpectedly differ");
        for (int32_t i = 0; i < root.scriptStartsLength; ++i)
            require(owner->scriptStarts[i] == root.scriptStarts[i], "Fixed ICU script starts unexpectedly differ");
        require(&owner->nfcImpl == &root.nfcImpl, "Fixed ICU owners require distinct FCD data");
    }
    export77::write_scripts((directory / "scripts.bin").string(), root);
}

void owner_json(std::ostream& out, const CollationData& data, size_t id, const Registry& registry) {
    std::array<uint32_t, 17> tags{};
    size_t range_count = 0;
    uint32_t previous = 0;
    for (uint32_t cp = 0; cp <= 0x10ffff; ++cp) {
        const uint32_t value = data.getCE32(cp);
        if (cp == 0 || value != previous) { ++range_count; previous = value; }
        ++tags[Collation::isSpecialCE32(value) ? Collation::tagFromCE32(value) : 16];
    }
    out << "{\"id\":" << id << ",\"base\":";
    if (data.base) out << registry.identifiers.at(data.base); else out << "null";
    out << ",\"numeric_primary\":" << data.numericPrimary << ",\"ce32_ranges\":" << range_count
        << ",\"ce32s\":" << data.ce32sLength << ",\"ces\":" << data.cesLength
        << ",\"raw_context_units\":" << data.contextsLength
        << ",\"jamo_shares_base\":" << (data.base && data.jamoCE32s == data.base->jamoCE32s ? "true" : "false")
        << ",\"compressible_shares_base\":" << (data.base && data.compressibleBytes == data.base->compressibleBytes ? "true" : "false")
        << ",\"nfc_shares_root\":" << (&data.nfcImpl == &registry.owners.front()->nfcImpl ? "true" : "false")
        << ",\"codepoint_ce32_tag_counts\":";
    numbers(out, tags.data(), tags.size());
    out << ",\"num_scripts\":" << data.numScripts << ",\"scripts_index\":";
    numbers(out, data.scriptsIndex, data.numScripts + 16);
    out << ",\"script_starts\":";
    numbers(out, data.scriptStarts, data.scriptStartsLength);
    out << '}';
}
}  // namespace

int main(int argc, char** argv) try {
    require(argc >= 3 && argc <= 5, "usage: inventory-locales OUTPUT.json RESOURCE_NAMES.txt [DATA_DIR] [EXTRA_REQUESTS.txt]");
    versions();
    int32_t count = 0;
    const auto* locales = icu::Locale::getAvailableLocales(count);
    std::vector<std::string> all_locales;
    for (int32_t i = 0; i < count; ++i) all_locales.emplace_back(locales[i].getName());
    locales = icu::Collator::getAvailableLocales(count);
    std::vector<std::string> collation_locales;
    for (int32_t i = 0; i < count; ++i) collation_locales.emplace_back(locales[i].getName());
    UErrorCode status = U_ZERO_ERROR;
    const auto global_types = enumeration(icu::Collator::getKeywordValues("collation", status), status);
    std::set<std::string> bases(all_locales.begin(), all_locales.end());
    bases.insert(collation_locales.begin(), collation_locales.end()); bases.insert("root");
    const auto resource_names = lines(argv[2]);
    bases.insert(resource_names.begin(), resource_names.end());
    std::set<std::string> requests;
    std::vector<std::string> resource_rows;
    for (const auto& name : resource_names) {
        const auto resource = export77::inspect_resource(name);
        resource_rows.push_back(resource_json(resource));
        for (const auto& type : resource.types) {
            if (type.resource_type == URES_TABLE || type.resource_type == URES_ALIAS)
                add_type(requests, icu::Locale::createFromName(name.c_str()), type.name);
        }
    }
    if (argc == 5) for (const auto& requested : lines(argv[4])) requests.insert(requested);
    std::vector<std::string> type_rows;
    for (const auto& base : bases) {
        const icu::Locale locale = icu::Locale::createFromName(base.c_str());
        status = U_ZERO_ERROR;
        const auto types = enumeration(icu::Collator::getKeywordValuesForLocale("collation", locale, false, status), status);
        std::ostringstream row;
        row << "{\"locale\":" << quote(base) << ",\"types\":";
        strings(row, types); row << '}'; type_rows.push_back(row.str());
        requests.insert(base);
        for (const auto& type : types) add_type(requests, locale, type);
        // Include public type requests which fall back in this locale as well.
        for (const auto& type : global_types) add_type(requests, locale, type);
    }
    Registry registry;
    const auto* root = icu::CollationRoot::getData(status);
    check(status, "register root data");
    require(root != nullptr, "Missing root data"); registry.owner(root);
    std::vector<std::string> request_rows;
    for (const auto& requested : requests) request_rows.push_back(request_json(requested, registry));
    std::ofstream out(argv[1]);
    require(out.good(), "Cannot create locale inventory");
    out << "{\n\"schema\":\"boostregexrs.icu77-locale-inventory.v2\",\n"
        << "\"icu\":\"77.1\",\"unicode\":\"16.0.0\",\"cldr\":\"47.0\",\"icu_data\":\"77.1\",\n"
        << "\"process_default_locale\":" << quote(icu::Locale::getDefault().getName()) << ",\n\"all_icu_locales\":";
    strings(out, all_locales); out << ",\n\"collation_available_locales\":"; strings(out, collation_locales);
    out << ",\n\"global_collation_types\":"; strings(out, global_types);
    auto section = [&](const char* name, const std::vector<std::string>& values) {
        out << ",\n" << quote(name) << ":[\n";
        for (size_t i = 0; i < values.size(); ++i) out << (i ? ",\n" : "") << values[i];
        out << "\n]";
    };
    section("resource_bundles", resource_rows); section("locale_types", type_rows);
    section("requests", request_rows); section("settings", registry.settings);
    out << ",\n\"owners\":[\n";
    for (size_t i = 0; i < registry.owners.size(); ++i) {
        if (i) out << ",\n";
        owner_json(out, *registry.owners[i], i, registry);
    }
    out << "\n]}\n"; out.flush(); require(out.good(), "Locale inventory write failed");
    if (argc >= 4) export_data(argv[3], registry);
    std::cout << "{\"known_icu_locales\":" << all_locales.size() << ",\"collation_locales\":"
              << collation_locales.size() << ",\"resource_bundles\":" << resource_rows.size()
              << ",\"locale_bases\":" << bases.size() << ",\"requests\":" << requests.size() << ",\"owners\":"
              << registry.owners.size() << ",\"settings\":" << registry.settings.size() << "}\n";
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
