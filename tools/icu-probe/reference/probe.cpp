// Project test utility. Reference APIs are from Boost.Regex 1.89.0 (BSL-1.0)
// and ICU 77.1 (Unicode-3.0); these libraries are external test dependencies.
#define BOOST_REGEX_NO_LIB
#include <boost/regex/icu.hpp>
#include <boost/version.hpp>
#include <unicode/ulocdata.h>
#include <unicode/uversion.h>
#include <unicode/udata.h>
#include <unicode/icudataver.h>
#include <unicode/uclean.h>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#else
#include <cerrno>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

static_assert(BOOST_VERSION == 108900, "Reference requires official Boost 1.89.0");

namespace fs = std::filesystem;
std::string version(const UVersionInfo v) { char b[U_MAX_VERSION_STRING_LENGTH]; u_versionToString(v, b); return b; }
void word(std::ofstream& out, std::uint32_t x) { char b[4]; for(int j=0;j<4;++j) b[j]=static_cast<char>((x>>(8*j))&255); out.write(b,4); }
std::string hex(const std::vector<UChar32>& values) { std::ostringstream out; bool first=true; for(auto x:values) { if(!first) out<<','; first=false; out << std::hex << std::setfill('0') << std::setw(8) << static_cast<std::uint32_t>(x); } return out.str(); }
std::vector<UChar32> utf8_hex(const std::string& text) {
  std::string bytes; for(size_t i=0;i<text.size();i+=2) bytes.push_back(static_cast<char>(std::stoi(text.substr(i,2),nullptr,16)));
  auto s=icu::UnicodeString::fromUTF8(icu::StringPiece(bytes.data(),static_cast<int32_t>(bytes.size())));
  std::vector<UChar32> out; for(int32_t i=0;i<s.length();) { auto c=s.char32At(i); out.push_back(c); i+=U16_LENGTH(c); } return out;
}
std::vector<UChar32> ascii(const std::string& s) { return {s.begin(),s.end()}; }
struct TransformCall { boost::icu_regex_traits* traits; const UChar32* first; const UChar32* last; bool primary; std::vector<UChar32>* output; };
void invoke_transform(void* opaque) { auto& c=*static_cast<TransformCall*>(opaque); *c.output=c.primary?c.traits->transform_primary(c.first,c.last):c.traits->transform(c.first,c.last); }
#if defined(_WIN32)
// Only this research executable catches native access violations, so one broken
// reference case can be recorded without replacing it with a fabricated key.
unsigned long native_call(void (*callback)(void*),void* context) { __try { callback(context); return 0; } __except(GetExceptionCode()==EXCEPTION_ACCESS_VIOLATION?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH) { return GetExceptionCode(); } }
std::string transform_result(boost::icu_regex_traits& traits,const UChar32* first,const UChar32* last,bool primary) { std::vector<UChar32> output; TransformCall c{&traits,first,last,primary,&output}; if(native_call(invoke_transform,&c)) return "ERROR:ACCESS_VIOLATION"; return hex(output); }
#else
// fork isolates the unmodified reference call. The parent records an actual
// signal/exit status; a signal handler must not resume potentially damaged C++.
std::string transform_result(boost::icu_regex_traits& traits, const UChar32* first,
                             const UChar32* last, bool primary) {
  int descriptors[2];
  if (pipe(descriptors) != 0) throw std::runtime_error("reference pipe failed");
  const auto child = fork();
  if (child == -1) {
    close(descriptors[0]); close(descriptors[1]);
    throw std::runtime_error("reference fork failed");
  }
  if (child == 0) {
    close(descriptors[0]);
    const rlimit no_core{0, 0};
    setrlimit(RLIMIT_CORE, &no_core);
    std::string result;
    try {
      std::vector<UChar32> output;
      TransformCall call{&traits, first, last, primary, &output};
      invoke_transform(&call);
      result = hex(output);
    } catch (const std::exception& error) {
      std::cerr << "Reference C++ exception: " << error.what() << '\n';
      result = "ERROR:CPP_EXCEPTION";
    } catch (...) {
      result = "ERROR:CPP_EXCEPTION";
    }
    std::size_t offset = 0;
    while (offset < result.size()) {
      const auto count = write(descriptors[1], result.data() + offset, result.size() - offset);
      if (count < 0 && errno == EINTR) continue;
      if (count <= 0) _exit(125);
      offset += static_cast<std::size_t>(count);
    }
    close(descriptors[1]);
    _exit(0);
  }
  close(descriptors[1]);
  std::string result;
  char buffer[4096];
  bool read_failed = false;
  for (;;) {
    const auto count = read(descriptors[0], buffer, sizeof(buffer));
    if (count < 0 && errno == EINTR) continue;
    if (count < 0) read_failed = true;
    if (count <= 0) break;
    result.append(buffer, static_cast<std::size_t>(count));
  }
  close(descriptors[0]);
  int status = 0;
  while (waitpid(child, &status, 0) < 0) {
    if (errno != EINTR) throw std::runtime_error("reference waitpid failed");
  }
  if (read_failed) throw std::runtime_error("reference pipe read failed");
  if (WIFSIGNALED(status)) return "ERROR:SIGNAL_" + std::to_string(WTERMSIG(status));
  if (!WIFEXITED(status)) throw std::runtime_error("unknown reference process status");
  if (WEXITSTATUS(status) != 0) return "ERROR:EXIT_" + std::to_string(WEXITSTATUS(status));
  if (result.empty()) throw std::runtime_error("empty reference process output");
  return result;
}
#endif

std::string compiler_identity() {
#if defined(_MSC_VER)
  return "MSVC " + std::to_string(_MSC_VER);
#elif defined(__clang__)
  return "Clang " __clang_version__;
#elif defined(__GNUC__)
  return "GCC " __VERSION__;
#else
  return "unknown C++ compiler";
#endif
}
int main(int argc,char** argv) try {
  if(argc!=3) throw std::runtime_error("usage: probe OUTPUT_DIR CASES_TSV");
  fs::path dir(argv[1]); fs::create_directories(dir);
  UErrorCode status=U_ZERO_ERROR; u_init(&status); if(U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
  UVersionInfo runtime{}, unicode{}, cldr{}, data{}; u_getVersion(runtime); u_getUnicodeVersion(unicode);
  ulocdata_getCLDRVersion(cldr,&status); u_getDataVersion(data,&status); if(U_FAILURE(status)) throw std::runtime_error(u_errorName(status));
  if(runtime[0]!=77||runtime[1]!=1||unicode[0]!=16||unicode[1]!=0||cldr[0]!=47||data[0]!=77||data[1]!=1) throw std::runtime_error("Unexpected reference version");
  std::ofstream meta(dir/"metadata.json");
  meta << "{\n  \"boost\": \"" << BOOST_LIB_VERSION << "\",\n  \"icu\": \""<<version(runtime)<<"\",\n  \"unicode\": \""<<version(unicode)<<"\",\n  \"cldr\": \""<<version(cldr)<<"\",\n  \"data\": \""<<version(data)<<"\",\n  \"default_locale\": \""<<icu::Locale::getDefault().getName()<<"\",\n  \"compiler\": \""<<compiler_identity()<<"\",\n  \"codepoint_records\": 1114112,\n  \"record_bytes\": 40\n}\n";
  std::ofstream cp(dir/"codepoints.bin",std::ios::binary);
  for(UChar32 c=0;c<=0x10ffff;++c) for(auto n : {c,u_tolower(c),u_toupper(c),u_foldCase(c,U_FOLD_CASE_DEFAULT),static_cast<int>(u_charType(c)),static_cast<int>(u_isblank(c)!=0),static_cast<int>(u_isspace(c)!=0),u_digit(c,10),u_digit(c,16),u_digit(c,36)}) word(cp,static_cast<std::uint32_t>(n));
  cp.close(); meta.close();
  if(!cp) throw std::runtime_error("codepoint write failed");
  std::vector<std::pair<std::string,std::vector<UChar32>>> cases; std::ifstream input(argv[2]); std::string line;
  while(std::getline(input,line)) { if(!line.empty()&&line.back()=='\r') line.pop_back(); if(line=="case_id\tutf8_hex") continue; auto tab=line.find('\t'); if(tab==std::string::npos) throw std::runtime_error("invalid case line"); cases.push_back({line.substr(0,tab),utf8_hex(line.substr(tab+1))}); }
  std::ofstream sorts(dir/"sortkeys.tsv"), locales(dir/"locales.tsv");
  sorts<<"locale\tcase_id\tprimary\tidentical\n"; locales<<"requested\timbue_previous\tgetloc\tsecond_imbue_previous\n";
  for(auto name : {"root","en_US","tr_TR","de_DE","sv_SE","fr_CA","es_ES@collation=traditional","zh_CN","ja_JP","th_TH"}) {
    boost::icu_regex_traits traits; auto requested=std::string(name)=="root"?icu::Locale::getRoot():icu::Locale::createFromName(name);
    auto previous=traits.imbue(requested); auto observed=traits.getloc();
    for(auto& item:cases) { auto text=item.second; const UChar32 empty=0; auto first=text.empty()?&empty:text.data(); auto last=first+text.size(); sorts<<name<<'\t'<<item.first<<'\t'<<transform_result(traits,first,last,true)<<'\t'<<transform_result(traits,first,last,false)<<'\n'; }
    auto second_previous=traits.imbue(icu::Locale::getRoot()); locales<<name<<'\t'<<previous.getName()<<'\t'<<observed.getName()<<'\t'<<second_previous.getName()<<'\n';
  }
  std::ofstream names(dir/"names.tsv"); names<<"name\tu32_hex\n";
  for(auto name:{"LATIN SMALL LETTER A","latin small letter a","GRINNING FACE","CJK UNIFIED IDEOGRAPH-4E2D","HANGUL SYLLABLE GA","<control-0000>","<surrogate-D800>","<noncharacter-FFFF>","<reserved-0378>","LINE FEED (LF)","NUL","newline","tab","a","THIS NAME DOES NOT EXIST"}) { boost::icu_regex_traits traits; auto s=ascii(name); names<<name<<'\t'<<hex(traits.lookup_collatename(s.data(),s.data()+s.size()))<<'\n'; }
  sorts.close(); locales.close(); names.close();
  if (!sorts || !locales || !names) throw std::runtime_error("reference output write failed");
  std::cout<<"ICU "<<version(runtime)<<", Unicode "<<version(unicode)<<", CLDR "<<version(cldr)<<"; wrote "<<cases.size()*20<<" sort keys and 1114112 codepoint records\n";
} catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
