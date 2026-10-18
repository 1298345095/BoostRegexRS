// Development-only inspection of ICU77's actual primary reordering fields.
// Source/license identity: ../data/NOTICE.md and ../data/LICENSE-ICU.txt.
#include <cstdint>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "collationroot.h"
#include "collationtailoring.h"
#include "collationsettings.h"
#include "../export/locale_data.h"

#if U_ICU_VERSION_MAJOR_NUM != 77 || U_ICU_VERSION_MINOR_NUM != 1
#error This diagnostic requires official ICU4C 77.1.
#endif

int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("usage: inspect-reorder DECIMAL_CODES OUTPUT.bin");
        std::vector<int32_t> codes;
        std::istringstream input(argv[1]);
        std::string item;
        while (std::getline(input, item, ',')) {
            size_t consumed = 0;
            auto value = std::stoll(item, &consumed);
            if (consumed != item.size() || value < INT32_MIN || value > INT32_MAX)
                throw std::runtime_error("Invalid i32 reorder code");
            codes.push_back(static_cast<int32_t>(value));
        }
        UErrorCode status = U_ZERO_ERROR;
        const auto* root = icu::CollationRoot::getRoot(status);
        if (U_FAILURE(status) || root == nullptr) throw std::runtime_error("Cannot load ICU root data");
        icu::CollationSettings settings(*root->settings);
        settings.setReordering(*root->data, codes.data(), static_cast<int32_t>(codes.size()), status);
        if (U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
        export77::write_settings(argv[2], settings);
        std::cout << u_errorName(status) << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "inspect-reorder: " << error.what() << '\n';
        return 1;
    }
}
