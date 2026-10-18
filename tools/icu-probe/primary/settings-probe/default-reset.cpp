// Minimal public-API reproducer for ICU77 default-reorder ownership cleanup.
// This intentionally invokes normal destruction; no failure is suppressed.
#include <iomanip>
#include <iostream>
#include <memory>
#include <vector>
#include <unicode/coll.h>
#include <unicode/uscript.h>
#include <unicode/uversion.h>

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This reproducer requires official ICU4C 77.1.
#endif

int main() {
    UErrorCode status = U_ZERO_ERROR;
    std::unique_ptr<icu::Collator> collator(icu::Collator::createInstance(icu::Locale("am"), status));
    if (U_FAILURE(status) || !collator) return 1;
    const int32_t requested[] = {USCRIPT_GREEK, USCRIPT_LATIN};
    collator->setReorderCodes(requested, 2, status);
    std::cout << "set_owned_reordering=" << u_errorName(status) << '\n' << std::flush;
    if (U_FAILURE(status)) return 2;
    const int32_t reset[] = {UCOL_REORDER_CODE_DEFAULT};
    collator->setReorderCodes(reset, 1, status);
    std::cout << "restore_default=" << u_errorName(status) << '\n' << std::flush;
    if (U_FAILURE(status)) return 3;
    const char16_t input[] = {u'a'};
    for (auto strength : {UCOL_PRIMARY, UCOL_SECONDARY, UCOL_TERTIARY, UCOL_QUATERNARY, UCOL_IDENTICAL}) {
        collator->setStrength(static_cast<icu::Collator::ECollationStrength>(strength));
        const auto length = collator->getSortKey(input, 1, nullptr, 0);
        if (length <= 0) return 4;
        std::vector<uint8_t> bytes(static_cast<size_t>(length));
        if (collator->getSortKey(input, 1, bytes.data(), length) != length) return 5;
        std::cout << "strength=" << std::dec << strength << " complete_key=" << std::hex << std::setfill('0');
        for (auto byte : bytes) std::cout << std::setw(2) << static_cast<unsigned>(byte);
        std::cout << '\n' << std::flush;
    }
    std::cout << "begin_normal_destruction\n" << std::flush;
    collator.reset();
    std::cout << "normal_destruction_completed\n" << std::flush;
    return 0;
}
