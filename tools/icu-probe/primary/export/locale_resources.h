// Inspect raw ICU resources before alias substitution or locale fallback.
// Uses fixed ICU77 internal resource readers only in this development exporter.
#ifndef BOOSTREGEXRS_LOCALE_RESOURCES_H
#define BOOSTREGEXRS_LOCALE_RESOURCES_H

#include <string>
#include <vector>
#include <unicode/unistr.h>
#include "uresdata.h"
#include "ucol_imp.h"
#include "locale_data.h"

namespace export77 {
class RawResource {
public:
    explicit RawResource(const std::string& name) {
        try {
            UErrorCode status = U_ZERO_ERROR;
            res_load(&data, U_ICUDATA_COLL, name.c_str(), &status);
            require(U_SUCCESS(status), "Cannot load listed raw collation resource");
            if (data.usesPoolBundle) {
                res_load(&pool_, U_ICUDATA_COLL, "pool", &status);
                require(U_SUCCESS(status) && pool_.isPoolBundle, "Cannot load collation resource pool");
                const int32_t* indexes = pool_.pRoot + 1;
                require(data.pRoot[1 + URES_INDEX_POOL_CHECKSUM] == indexes[URES_INDEX_POOL_CHECKSUM],
                        "Raw collation resource pool checksum mismatch");
                data.poolBundleKeys = reinterpret_cast<const char*>(indexes + (indexes[URES_INDEX_LENGTH] & 0xff));
                data.poolBundleStrings = pool_.p16BitUnits;
            }
        } catch (...) { res_unload(&data); res_unload(&pool_); throw; }
    }
    ~RawResource() { res_unload(&data); res_unload(&pool_); }
    RawResource(const RawResource&) = delete;
    RawResource& operator=(const RawResource&) = delete;
    ResourceData data{};
private:
    ResourceData pool_{};
};

inline Resource child(const ResourceData& data, Resource table, const char* name) {
    int32_t index = -1;
    return res_getTableItemByKey(&data, table, &index, &name);
}

inline std::string resource_text(const ResourceData& data, Resource resource) {
    if (resource == RES_BOGUS) return {};
    int32_t length = 0;
    const auto* value = res_getPublicType(resource) == URES_ALIAS
        ? res_getAlias(&data, resource, &length) : res_getStringNoTrace(&data, resource, &length);
    require(value != nullptr, "Expected string or alias in collation resource metadata");
    std::string result;
    icu::UnicodeString(value, length).toUTF8String(result);
    return result;
}

struct ResourceType {
    std::string name;
    int32_t resource_type;
    std::string alias;
    std::string string_value;
    bool has_binary;
    int32_t binary_bytes;
    std::vector<std::string> keys;
};
struct ResourceInfo {
    std::string name;
    std::string alias;
    std::string parent;
    bool parent_is_root;
    bool no_fallback;
    std::string collations_alias;
    std::vector<std::string> keys;
    std::vector<ResourceType> types;
};

inline std::vector<std::string> resource_keys(const ResourceData& data, Resource table) {
    std::vector<std::string> result;
    for (int32_t i = 0; i < res_countArrayItems(&data, table); ++i) {
        const char* key = nullptr;
        require(res_getTableItemByIndex(&data, table, i, &key) != RES_BOGUS && key,
                "Cannot enumerate complete raw collation resource table");
        result.emplace_back(key);
    }
    return result;
}

inline ResourceInfo inspect_resource(const std::string& name) {
    RawResource bundle(name);
    const auto& data = bundle.data;
    ResourceInfo result{name, resource_text(data, res_getResource(&data, "%%ALIAS")),
                        resource_text(data, res_getResource(&data, "%%Parent")),
                        res_getResource(&data, "%%ParentIsRoot") != RES_BOGUS,
                        bool(data.noFallback), {}, resource_keys(data, data.rootRes), {}};
    const auto collations = res_getResource(&data, "collations");
    if (collations == RES_BOGUS) return result;
    if (res_getPublicType(collations) == URES_ALIAS) {
        result.collations_alias = resource_text(data, collations);
        return result;
    }
    require(res_getPublicType(collations) == URES_TABLE, "Unexpected raw collations resource type");
    for (const auto& key : resource_keys(data, collations)) {
        const auto value = child(data, collations, key.c_str());
        ResourceType row{key, res_getPublicType(value), {}, {}, false, 0, {}};
        if (row.resource_type == URES_ALIAS) row.alias = resource_text(data, value);
        else if (row.resource_type == URES_STRING) row.string_value = resource_text(data, value);
        else if (row.resource_type == URES_TABLE) {
            row.keys = resource_keys(data, value);
            const auto binary = child(data, value, "%%CollationBin");
            row.has_binary = binary != RES_BOGUS;
            if (row.has_binary) require(res_getBinaryNoTrace(&data, binary, &row.binary_bytes) != nullptr,
                                        "Collation binary resource has unexpected type");
        }
        result.types.push_back(std::move(row));
    }
    return result;
}
}  // namespace export77
#endif
