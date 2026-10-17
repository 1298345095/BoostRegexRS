// Isolated empty-input diagnostic; never substitutes for Boost oracle output.
#define BOOST_REGEX_NO_LIB
#include <boost/regex/icu.hpp>
#include <iostream>
#include <iomanip>
#include <memory>
int main(int argc,char** argv) {
    if(argc!=2) return 2;
    std::string mode=argv[1];
    if(mode=="boost_primary"||mode=="boost_identical") {
        boost::icu_regex_traits traits; traits.imbue(icu::Locale::getRoot());
        // A valid empty iterator range; Boost internally converts it to nullptr,0.
        const UChar32 sentinel=0;
        auto key=mode=="boost_primary"?traits.transform_primary(&sentinel,&sentinel):traits.transform(&sentinel,&sentinel);
        std::cout<<"length="<<key.size()<<" key=";
        for(auto c:key) std::cout<<std::hex<<std::setfill('0')<<std::setw(8)<<static_cast<std::uint32_t>(c)<<',';
    } else {
        UErrorCode status=U_ZERO_ERROR;
        std::unique_ptr<icu::Collator> coll(icu::Collator::createInstance(icu::Locale::getRoot(),status));
        if(U_FAILURE(status)) return 3;
        coll->setStrength(icu::Collator::IDENTICAL);
        const UChar sentinel=0; std::uint8_t key[100];
        auto length=coll->getSortKey(mode=="icu_null"?nullptr:&sentinel,0,key,100);
        std::cout<<"length="<<length<<" key=";
        for(int i=0;i<length;++i) std::cout<<std::hex<<std::setfill('0')<<std::setw(2)<<static_cast<unsigned>(key[i])<<',';
    }
    std::cout<<'\n';
}
