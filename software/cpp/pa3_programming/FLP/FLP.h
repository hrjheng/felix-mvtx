#include <stdio.h>
#include <thread>
#include <string>
#include <cstring>
#include <ctime>
#include <list>
#include <nlohmann/json.hpp>

#ifndef FLP_H
#define FLP_H

using json = nlohmann::json;

class FLP
{
    public:

    struct CRU {
        std::string card_id;
        std::string endpoint;
        std::list<int> gbt_chs;
    };

    std::list<CRU> list_cru;

    std::string exec(char* cmd);
    json get_roc_list_cards();
    json get_roc_status(int card);
    void enum_cru();
    void print_found_chs();
};

#endif
