// Public Boost 1.89 traits scope check for the ICU77 DEFAULT cleanup failure.
// Every collator and traits instance is destroyed normally.
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
#include <boost/regex/icu.hpp>
#include <boost/version.hpp>

#if BOOST_VERSION != 108900 || U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This scope check requires official Boost 1.89.0 and ICU4C 77.1.
#endif

static std::vector<UChar32> native_key(icu::Collator& collator, icu::Collator::ECollationStrength strength) {
    collator.setStrength(strength);
    const char16_t input[] = {u'a'};
    const auto length = collator.getSortKey(input, 1, nullptr, 0);
    if (length < 1) throw std::runtime_error("Native sort key length failed");
    std::vector<uint8_t> bytes(static_cast<size_t>(length));
    if (collator.getSortKey(input, 1, bytes.data(), length) != length) {
        throw std::runtime_error("Native sort key length changed");
    }
    // Exact Boost do_transform packaging, for a nonempty source string.
    if (bytes.size() > 1 && bytes.back() == 0) bytes.pop_back();
    return {bytes.begin(), bytes.end()};
}

static void print_key(const char* name, const std::vector<UChar32>& key) {
    std::cout << name << '=' << std::hex << std::setfill('0');
    for (auto value : key) std::cout << std::setw(2) << static_cast<unsigned>(value);
    std::cout << '\n' << std::dec << std::flush;
}

int main() {
    try {
        auto traits = std::make_unique<boost::icu_regex_traits>();
        const UChar32 input[] = {0x61};
        for (const char* name : {"am", "am@colReorder=Grek-Latn", "am"}) {
            const icu::Locale locale(name);
            UErrorCode status = U_ZERO_ERROR;
            std::unique_ptr<icu::Collator> audit(icu::Collator::createInstance(locale, status));
            if (U_FAILURE(status) || !audit) throw std::runtime_error("Locale collator creation failed");
            int32_t codes[256];
            const auto length = audit->getReorderCodes(codes, 256, status);
            if (U_FAILURE(status)) throw std::runtime_error("Locale reorder query failed");
            std::cout << "locale=" << name << " effective_reorder_codes=";
            for (int32_t i = 0; i < length; ++i) {
                if (i != 0) std::cout << ',';
                std::cout << codes[i];
            }
            std::cout << '\n' << std::flush;
            traits->imbue(locale);
            const auto primary = traits->transform_primary(input, input + 1);
            const auto identical = traits->transform(input, input + 1);
            if (primary != native_key(*audit, icu::Collator::PRIMARY) ||
                identical != native_key(*audit, icu::Collator::IDENTICAL)) {
                throw std::runtime_error("Complete Boost key differs from its fresh locale reference");
            }
            print_key("boost_primary", primary);
            print_key("boost_identical", identical);
            audit.reset();
            std::cout << "fresh_reference_destruction_completed\n" << std::flush;
        }
        std::cout << "begin_boost_traits_destruction\n" << std::flush;
        traits.reset();
        std::cout << "boost_traits_destruction_completed\n" << std::flush;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
