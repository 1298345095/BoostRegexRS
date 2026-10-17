#include <boost/regex.hpp>
#include <boost/version.hpp>
#include <windows.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static_assert(BOOST_VERSION == 108900, "requires official Boost 1.89.0");
volatile std::uint64_t sink = 0;
using Clock = std::chrono::steady_clock;
double cpu_ns() {
  FILETIME creation, exit, kernel, user;
  if (!GetProcessTimes(GetCurrentProcess(), &creation, &exit, &kernel, &user))
    throw std::runtime_error("GetProcessTimes failed");
  ULARGE_INTEGER k{}, u{};
  k.LowPart = kernel.dwLowDateTime; k.HighPart = kernel.dwHighDateTime;
  u.LowPart = user.dwLowDateTime; u.HighPart = user.dwHighDateTime;
  return static_cast<double>(k.QuadPart + u.QuadPart) * 100.0;
}
struct Sample { double wall_ns, cpu_ns; std::uint64_t sum; };
template<class F> Sample batch(F& op, std::size_t n) {
  std::uint64_t sum = 0;
  const auto c0 = cpu_ns(); const auto t0 = Clock::now();
  for (std::size_t i = 0; i < n; ++i) sum += op();
  const auto t1 = Clock::now(); const auto c1 = cpu_ns();
  sink = sum;
  return {std::chrono::duration<double, std::nano>(t1-t0).count(), c1-c0, sum};
}
template<class F> void run(const char* name, std::size_t bytes, std::uint64_t expected, F op) {
  if (op() != expected) throw std::runtime_error(std::string("wrong expected: ") + name);
  batch(op, 100);
  std::size_t n = 100;
  while (batch(op, n).wall_ns < 250e6 && n < 104857600) n *= 2;
  std::vector<double> wall, cpu;
  std::uint64_t total = 0;
  for (int j=0; j<9; ++j) {
    const auto x = batch(op, n);
    if (x.sum != expected * n) throw std::runtime_error("checksum mismatch");
    wall.push_back(x.wall_ns/n); cpu.push_back(x.cpu_ns/n); total += x.sum;
  }
  std::sort(wall.begin(),wall.end()); std::sort(cpu.begin(),cpu.end());
  std::cout << name << ',' << bytes << ',' << n << ",9," << wall[4] << ',' << wall[8]
    << ',' << cpu[4] << ',' << total << '\n';
}
int main() {
  std::cerr << "Boost " << BOOST_LIB_VERSION << "; _MSC_VER=" << _MSC_VER << "; char bits=8; default traits; no ICU\n";
  std::cout << "case,input_bytes,iterations_per_batch,batches,wall_median_ns,wall_max_ns,cpu_median_ns,checksum\n" << std::fixed << std::setprecision(2);
  const std::string simple_pattern = "([A-Za-z_][A-Za-z_0-9]*)=([0-9]+)";
  const std::string complex_pattern = "^(?=.{1,64}$)([a-z]+)-\\1$";
  run("compile_ascii", simple_pattern.size(), 2, [&] { return boost::regex(simple_pattern).mark_count(); });
  run("compile_lookahead_backref", complex_pattern.size(), 1, [&] { return boost::regex(complex_pattern).mark_count(); });
  const std::string short_input = "prefix user_name=12345 suffix";
  const boost::regex simple(simple_pattern), complex(complex_pattern), missing("needle[0-9]+"), repl("([a-z]+)=([0-9]+)");
  boost::smatch check;
  if (!boost::regex_search(short_input,check,simple) || check[1] != "user_name" || check[2] != "12345")
    throw std::runtime_error("capture preflight failed");
  run("search_short_hit", short_input.size(), 1, [&] { return boost::regex_search(short_input, simple) ? 1 : 0; });
  run("captures_short_hit", short_input.size(), 24, [&] {
    boost::smatch m;
    if (!boost::regex_search(short_input,m,simple)) return std::size_t(0);
    return m.position() + m.length(1) + m.length(2) + m.size();
  });
  const std::string large_miss(1024*1024,'x');
  run("search_1mib_miss", large_miss.size(), 0, [&] { return boost::regex_search(large_miss,missing) ? 1 : 0; });
  const std::string backref_input = "abcdefghijkl-abcdefghijkl";
  run("lookahead_backref_hit", backref_input.size(), 1, [&] { return boost::regex_match(backref_input,complex) ? 1 : 0; });
  const boost::regex backtracking("^(a|aa)+$");
  const std::string bounded_failure = std::string(18,'a') + 'b';
  run("bounded_backtracking_miss", bounded_failure.size(), 0, [&] { return boost::regex_match(bounded_failure,backtracking) ? 1 : 0; });
  const std::string replace_short = "alpha=12 beta=345";
  const std::string format = "$2:$1";
  run("replace_short_global",replace_short.size(),17,[&] {
    const auto s=boost::regex_replace(replace_short,repl,format);
    return s == "12:alpha 345:beta" ? s.size() : std::size_t(0);
  });
  std::string replace_large;
  for (int i=0;i<16384;++i) replace_large += "alpha=12 beta=3\n";
  std::string expected_large;
  for (int i=0;i<16384;++i) expected_large += "12:alpha 3:beta\n";
  if (boost::regex_replace(replace_large,repl,format) != expected_large)
    throw std::runtime_error("large replacement preflight failed");
  run("replace_256kib_global",replace_large.size(),expected_large.size()+std::uint64_t('1')+std::uint64_t('\n'),[&] {
    const auto s=boost::regex_replace(replace_large,repl,format);
    return s.size()+std::uint64_t(s.front())+std::uint64_t(s.back());
  });
}
