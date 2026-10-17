// Development-only reference for official Boost.Regex 1.89.0.
// SPDX-License-Identifier: BSL-1.0
#define BOOST_REGEX_MATCH_EXTRA
#include <boost/regex.hpp>
#include <boost/version.hpp>

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#if BOOST_VERSION != 108900
#error This reference requires official Boost 1.89.0
#endif

namespace {
using Regex = boost::basic_regex<char, boost::cpp_regex_traits<char>>;
using Iterator = std::string::const_iterator;
using Matches = boost::match_results<Iterator>;
constexpr const char* input_header =
    "case_id\toperation\tsyntax\tmatch\tpattern_hex\tinput_hex\tformat_hex";

unsigned nibble(char value) {
    if (value >= '0' && value <= '9') return static_cast<unsigned>(value - '0');
    if (value >= 'a' && value <= 'f') return static_cast<unsigned>(value - 'a' + 10);
    if (value >= 'A' && value <= 'F') return static_cast<unsigned>(value - 'A' + 10);
    throw std::invalid_argument("Invalid hexadecimal input");
}

std::string unhex(const std::string& value) {
    if ((value.size() % 2) != 0) throw std::invalid_argument("Odd hexadecimal width");
    std::string result;
    result.reserve(value.size() / 2);
    for (std::size_t i = 0; i < value.size(); i += 2) {
        result.push_back(static_cast<char>((nibble(value[i]) << 4) | nibble(value[i + 1])));
    }
    return result;
}

std::string hex(const std::string& value) {
    constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(value.size() * 2);
    for (unsigned char byte : value) {
        result.push_back(digits[byte >> 4]);
        result.push_back(digits[byte & 15]);
    }
    return result;
}

std::uint32_t number(const std::string& value) {
    if (value.empty()) throw std::invalid_argument("Empty flags field");
    std::uint64_t result = 0;
    for (char item : value) {
        if (item < '0' || item > '9') throw std::invalid_argument("Flags must be unsigned decimal");
        result = result * 10 + static_cast<unsigned>(item - '0');
        if (result > UINT32_MAX) throw std::invalid_argument("Flags exceed u32");
    }
    return static_cast<std::uint32_t>(result);
}

std::vector<std::string> fields(const std::string& line) {
    std::vector<std::string> result;
    std::size_t start = 0;
    for (;;) {
        const auto end = line.find('\t', start);
        result.push_back(line.substr(start, end == std::string::npos ? end : end - start));
        if (end == std::string::npos) return result;
        start = end + 1;
    }
}

void range(std::ostream& out, Iterator base, Iterator first, Iterator last) {
    out << '[' << std::distance(base, first) << ',' << std::distance(base, last) << ']';
}

void match_json(std::ostream& out, const Matches& match, Iterator base, bool extra) {
    out << "{\"range\":";
    range(out, base, match[0].first, match[0].second);
    out << ",\"partial\":" << (match[0].matched ? "false" : "true") << ",\"groups\":[";
    for (std::size_t i = 0; i < match.size(); ++i) {
        if (i) out << ',';
        if (match[i].matched) range(out, base, match[i].first, match[i].second);
        else out << "null";
    }
    out << "],\"histories\":[";
    for (std::size_t i = 0; i < match.size(); ++i) {
        if (i) out << ',';
        out << '[';
        if (extra) {
            const auto& history = match.captures(static_cast<int>(i));
            for (std::size_t j = 0; j < history.size(); ++j) {
                if (j) out << ',';
                range(out, base, history[j].first, history[j].second);
            }
        }
        out << ']';
    }
    out << "],\"prefix\":";
    range(out, base, match.prefix().first, match.prefix().second);
    out << ",\"suffix\":";
    range(out, base, match.suffix().first, match.suffix().second);
    out << '}';
}

struct Request {
    std::string operation, pattern, input, format;
    std::uint32_t syntax, flag_bits;
};

Request parse(const std::vector<std::string>& row) {
    if (row.size() != 7) throw std::invalid_argument("Expected seven input columns");
    const auto& operation = row[1];
    if (operation != "compile" && operation != "search" && operation != "match"
        && operation != "iterate" && operation != "format" && operation != "replace") {
        throw std::invalid_argument("Unknown operation");
    }
    return {operation, unhex(row[4]), unhex(row[5]), unhex(row[6]), number(row[2]), number(row[3])};
}

std::string execute(const Request& request) {
    const auto flags = static_cast<boost::match_flag_type>(request.flag_bits);
    const auto& pattern = request.pattern;
    const auto& input = request.input;
    const auto& format = request.format;
    Regex regex;
    regex.imbue(std::locale::classic());
    regex.assign(pattern.begin(), pattern.end(), request.syntax);
    std::ostringstream out;
    out << "{\"mark_count\":" << regex.mark_count();
    if (request.operation == "compile") {
        out << ",\"compile_status\":" << regex.status() << '}';
        return out.str();
    }
    if (request.operation == "replace") {
        out << ",\"output_hex\":\"" << hex(boost::regex_replace(input, regex, format, flags)) << "\"}";
        return out.str();
    }
    const bool extra = (flags & boost::match_extra) != 0;
    out << ",\"matches\":[";
    if (request.operation == "iterate") {
        boost::regex_iterator<Iterator, char, boost::cpp_regex_traits<char>> current(input.begin(), input.end(), regex, flags), end;
        bool first = true;
        for (; current != end; ++current) {
            if (!first) out << ',';
            first = false;
            match_json(out, *current, input.begin(), extra);
        }
    } else {
        Matches match;
        bool found;
        if (request.operation == "match") found = boost::regex_match(input.begin(), input.end(), match, regex, flags);
        else found = boost::regex_search(input.begin(), input.end(), match, regex, flags);
        if (found) match_json(out, match, input.begin(), extra);
        if (request.operation == "format") {
            out << "],\"output_hex\":\"" << (found ? hex(match.format(format, flags)) : "") << "\"}";
            return out.str();
        }
    }
    out << "]}";
    return out.str();
}

void write_row(const std::vector<std::string>& row) {
    const auto& id = row.front();
    Request request;
    try {
        request = parse(row);
    } catch (const std::invalid_argument& error) {
        std::cout << id << "\tprotocol_error\t{\"message_hex\":\"" << hex(error.what()) << "\"}" << std::endl;
        return;
    }
    try {
        const auto result = execute(request);
        std::cout << id << "\tok\t" << result << std::endl;
    } catch (const boost::regex_error& error) {
        std::cout << id << "\tcompile_error\t{\"code\":" << error.code()
                  << ",\"position\":" << error.position() << '}' << std::endl;
    } catch (const std::invalid_argument& error) {
        // perl_matcher_common.hpp::construct_init checks the invalid object.
        std::cout << id << "\toperation_error\t{\"category\":\"invalid_argument\",\"position\":null,\"message_hex\":\""
                  << hex(error.what()) << "\"}" << std::endl;
    } catch (const std::logic_error& error) {
        // verify_options / construct_init reject incompatible match policies.
        // This adapter accesses match_results only after successful matching.
        std::cout << id << "\toperation_error\t{\"category\":\"invalid_match_options\",\"position\":null,\"message_hex\":\""
                  << hex(error.what()) << "\"}" << std::endl;
    } catch (const std::runtime_error& error) {
        std::cout << id << "\treference_resource_error\t{\"message_hex\":\"" << hex(error.what()) << "\"}" << std::endl;
    }
}
}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--metadata") {
        std::cout << "{\"boost\":\"" << BOOST_LIB_VERSION
                  << "\",\"traits\":\"cpp_regex_traits<char>\",\"locale\":\"C\","
                     "\"capture_history_compiled\":true,\"cxx_standard\":" << __cplusplus << "}\n";
        return 0;
    }
    if (argc != 1) return 2;
    std::string line;
    if (!std::getline(std::cin, line)) return 2;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line != input_header) return 2;
    std::cout << "case_id\tstatus\tresult\n";
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        write_row(fields(line));
    }
    return std::cin.bad() ? 2 : 0;
}
