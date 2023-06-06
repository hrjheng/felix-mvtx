#include "FLP.h"
#include <nlohmann/json.hpp>
#include <iostream>
#include <iomanip>
#include <string>

using json = nlohmann::json;

std::string FLP::exec(char* cmd) {
    std::shared_ptr<FILE> pipe(popen(cmd, "r"), pclose);
    if (!pipe) return "ERROR";
    char buffer[512];
    std::string result = "";
    while (!feof(pipe.get())) {
        if (fgets(buffer, 512, pipe.get()) != NULL)
            result += buffer;
    }
    return result;
}

void FLP::enum_cru()
{
    std::cout << "Scanning CRU endpoints..." << std::endl;
    json roc_list_cards = this->get_roc_list_cards();

    int num_eps = roc_list_cards.size();
    std::cout << "Found " << std::to_string(num_eps) << " endpoints.\n";

    json status[num_eps];

    for (int i = 0; i < num_eps; i++){
        CRU s;
        status[i] = this->get_roc_status(i);
        s.card_id = status[i]["pciAddress"];
        s.endpoint = std::to_string(i);
        bool store = false;
        for (int j = 0; j < 12; j++) {
            json eps = status[i][std::to_string(j)];
            if (eps["gbtMux"] == "SWT"){
                if (eps["status"] == "UP"){
                    std::cout << "Found UP SWT link on EP: " << s.endpoint << " CH: " << std::to_string(j) << std::endl;
                    s.gbt_chs.push_back(j);
                    store = true;
                }
            }
        }
        if (store){
            list_cru.push_back(s);
        }
    }
}
json FLP::get_roc_list_cards()
{
    return json::parse(exec((char*)"o2-roc-list-cards --json").c_str());
}

json FLP::get_roc_status(int card)
{
    std::string cmd = "o2-roc-status --id=#" + std::to_string(card) + " --json";
    return json::parse(exec((char*)cmd.c_str()).c_str());
}


void FLP::print_found_chs()
{
    std::cout << "========" << std::endl;
    for (auto const& it : list_cru) {
        std::cout << "Card ID: " << it.card_id << " EP: " << it.endpoint << std::endl;
        for (auto const& i : it.gbt_chs) {
            std::cout << "CH: " << i << std::endl;
        }
        std::cout << "========" << std::endl;
    }
}