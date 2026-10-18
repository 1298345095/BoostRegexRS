// Development-only reference for official Boost.Regex 1.89.0.
// SPDX-License-Identifier: BSL-1.0
#define BOOST_REGEX_MATCH_EXTRA
#include <boost/regex.hpp>
#include <boost/version.hpp>

#include <cstdint>
#include <iomanip>
#include <iostream>
#include <locale>
#include <new>
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

struct Observation {
    const char* phase = "compile";
    bool compile_returned = false;
    Regex::size_type mark_count = 0;
    int compile_status = 0;
};

std::string execute(const Request& request, Observation& observation) {
    const auto flags = static_cast<boost::match_flag_type>(request.flag_bits);
    const auto& pattern = request.pattern;
    const auto& input = request.input;
    const auto& format = request.format;
    Regex regex;
    regex.imbue(std::locale::classic());
    regex.assign(pattern.begin(), pattern.end(), request.syntax);
    // no_except returns an invalid compiled object. Preserve that API outcome
    // before a later matcher or serialization failure can obscure its status.
    observation.mark_count = regex.mark_count();
    observation.compile_status = regex.status();
    observation.compile_returned = true;
    observation.phase = "serialize";
    std::ostringstream out;
    out << "\"mark_count\":" << observation.mark_count;
    if (request.operation == "compile") {
        out << ",\"compile_status\":" << observation.compile_status;
        return out.str();
    }
    if (request.operation == "replace") {
        observation.phase = "replace";
        const auto replaced = boost::regex_replace(input, regex, format, flags);
        observation.phase = "serialize";
        out << ",\"output_hex\":\"" << hex(replaced) << '"';
        return out.str();
    }
    const bool extra = (flags & boost::match_extra) != 0;
    out << ",\"matches\":[";
    if (request.operation == "iterate") {
        observation.phase = "iterate";
        boost::regex_iterator<Iterator, char, boost::cpp_regex_traits<char>> current(input.begin(), input.end(), regex, flags), end;
        bool first = true;
        for (; current != end; ++current) {
            observation.phase = "serialize";
            if (!first) out << ',';
            first = false;
            match_json(out, *current, input.begin(), extra);
            observation.phase = "iterate";
        }
    } else {
        Matches match;
        bool found;
        observation.phase = request.operation == "match" ? "match" : "search";
        if (request.operation == "match") found = boost::regex_match(input.begin(), input.end(), match, regex, flags);
        else found = boost::regex_search(input.begin(), input.end(), match, regex, flags);
        observation.phase = "serialize";
        if (found) match_json(out, match, input.begin(), extra);
        if (request.operation == "format") {
            observation.phase = "format";
            const auto formatted = found ? match.format(format, flags) : std::string();
            observation.phase = "serialize";
            out << "],\"output_hex\":\"" << hex(formatted) << '"';
            return out.str();
        }
    }
    observation.phase = "serialize";
    out << ']';
    return out.str();
}

bool resource_code(boost::regex_constants::error_type code) {
    using namespace boost::regex_constants;
    return code == error_space || code == error_size || code == error_complexity || code == error_stack;
}

std::string reference_failure(const char* phase, const char* kind,
                              const std::exception& error, const boost::regex_error* regex_error = nullptr) {
    std::ostringstream out;
    out << "\"schema\":\"boostregexrs.reference-failure.v1\",\"phase\":\""
        << phase << "\",\"kind\":\"" << kind << "\",\"code\":";
    if (regex_error) out << regex_error->code();
    else out << "null";
    out << ",\"position\":";
    if (regex_error) out << regex_error->position();
    else out << "null";
    out << ",\"message_hex\":\"" << hex(error.what()) << '"';
    return out.str();
}

std::string operation_error(const char* category, const std::exception& error) {
    std::ostringstream out;
    out << "\"category\":\"" << category << "\",\"position\":null,\"message_hex\":\""
        << hex(error.what()) << '"';
    return out.str();
}

void result_row(const std::string& id, const char* status, const std::string& members,
                const Request& request, const Observation& observation) {
    // Every executed result follows the same lifetime: assign may return, the
    // requested operation still runs, and both outcomes survive its row writer.
    // A returned status has no exception position; no such position is added.
    std::cout << id << '\t' << status << "\t{" << members;
    if (request.operation != "compile" && observation.compile_returned && observation.compile_status != 0) {
        std::cout << ",\"preceding_compile\":{\"mark_count\":" << observation.mark_count
                  << ",\"compile_status\":" << observation.compile_status << '}';
    }
    std::cout << '}' << std::endl;
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
    Observation observation;
    const auto emit = [&](const char* status, const std::string& members) {
        result_row(id, status, members, request, observation);
    };
    try {
        const auto result = execute(request, observation);
        emit("ok", result);
    } catch (const boost::regex_error& error) {
        // pattern_except.hpp preserves this dynamic type at matcher guards as
        // well as parser/creator failures. Resource limits are never ordinary
        // syntax rejections, including when they occur during compilation.
        if (resource_code(error.code())) {
            emit("reference_failure", reference_failure(observation.phase, "regex_resource", error, &error));
        } else if (std::string(observation.phase) == "compile") {
            std::ostringstream out;
            out << "\"code\":" << error.code() << ",\"position\":" << error.position();
            emit("compile_error", out.str());
        } else {
            emit("reference_failure", reference_failure(observation.phase, "regex", error, &error));
        }
    } catch (const std::bad_alloc& error) {
        emit("reference_failure", reference_failure(observation.phase, "allocation", error));
    } catch (const std::length_error& error) {
        // Container capacity failures are not incompatible match policies.
        emit("reference_failure", reference_failure(observation.phase, "capacity", error));
    } catch (const std::invalid_argument& error) {
        // perl_matcher_common.hpp::construct_init checks the invalid object.
        emit("operation_error", operation_error("invalid_argument", error));
    } catch (const std::logic_error& error) {
        // verify_options / construct_init reject incompatible match policies.
        // This adapter accesses match_results only after successful matching.
        emit("operation_error", operation_error("invalid_match_options", error));
    } catch (const std::runtime_error& error) {
        // cpp_regex_traits.hpp uses plain runtime_error for catalog failures;
        // the type alone does not identify resource exhaustion.
        emit("reference_failure", reference_failure(observation.phase, "runtime", error));
    }
}
}  // namespace

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--metadata") {
        std::cout << "{\"boost\":\"" << BOOST_LIB_VERSION
                  << "\",\"traits\":\"cpp_regex_traits<char>\",\"locale\":\"C\","
                     "\"capture_history_compiled\":true,\"cxx_standard\":" << __cplusplus
                  << ",\"reference_failure_schema\":\"boostregexrs.reference-failure.v1\","
                     "\"preceding_compile_outcome\":true}\n";
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
