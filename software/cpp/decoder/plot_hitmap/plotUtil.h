using namespace std;

vector<vector<int>> AllFEEID()
{
    vector<vector<int>> FEEIDs = {{0, 256, 512, 4099, 4355, 4611, 8198, 8199, 8454, 8455, 8710, 8711, 1, 257, 513, 4100, 4356, 4612, 8200, 8201, 8456, 8457, 8712, 8713}, {2, 258, 514, 4101, 4102, 4357, 4358, 4613, 4614, 8202, 8458, 8714, 3, 259, 515, 4103, 4359, 4615, 8203, 8204, 8459, 8460, 8715, 8716},
                                  {4, 260, 516, 4104, 4105, 4360, 4361, 4616, 4617, 8205, 8461, 8717, 5, 261, 517, 4106, 4362, 4618, 8206, 8207, 8462, 8463, 8718, 8719}, {6, 262, 518, 4107, 4363, 4619, 8208, 8209, 8464, 8465, 8720, 8721, 7, 263, 519, 4108, 4364, 4620, 8210, 8211, 8466, 8467, 8722, 8723},
                                  {8, 264, 520, 4109, 4110, 4365, 4366, 4621, 4622, 8192, 8448, 8704, 9, 265, 521, 4111, 4367, 4623, 8193, 8194, 8449, 8450, 8705, 8706}, {10, 266, 522, 4096, 4097, 4352, 4353, 4608, 4609, 8195, 8451, 8707, 11, 267, 523, 4098, 4354, 4610, 8196, 8197, 8452, 8453, 8708, 8709}};

    return FEEIDs;
}

std::multimap<int, vector<int>> FEEIDtoLayerStave()
{
    vector<vector<int>> FEEIDs = AllFEEID();
    std::multimap<int, vector<int>> _FEEIDtoLayerStave;

    for (int flx = 0; flx < 6; flx++)
    {
        for (int i = 0; i < FEEIDs[flx].size(); i++)
        {
            int feeid = FEEIDs[flx][i];
            int layer = static_cast<int>((static_cast<uint32_t>(feeid) & 0x7000) >> 12);
            int gbt_channel = static_cast<int>((static_cast<uint32_t>(feeid) & 0x0300) >> 8);
            int stave = static_cast<int>(static_cast<uint32_t>(feeid) & 0x003f);

            vector<int> layerstave = {layer, stave};
            _FEEIDtoLayerStave.insert(std::make_pair(feeid, layerstave));
        }
    }

    return _FEEIDtoLayerStave;
}

std::vector<int> FEEID_ChipIDs(int feeid)
{
    if ((feeid >= 0 && feeid <= 11) || (feeid >= 4096 && feeid <= 4111) || (feeid >= 8192 && feeid <= 8211))
    {
        std::vector<int> chipids = {0, 1, 2}; 
        return chipids;
    }
    else if ((feeid >= 256 && feeid <= 267) || (feeid >= 4352 && feeid <= 4367) || (feeid >= 8448 && feeid <= 8467))
    {
        std::vector<int> chipids = {3, 4, 5}; 
        return chipids;
    }
    else if ((feeid >= 512 && feeid <= 523) || (feeid >= 4608 && feeid <= 4623) || (feeid >= 8704 && feeid <= 8723))
    {
        std::vector<int> chipids = {6, 7, 8}; 
        return chipids;
    }
    else
    {
        cout << "ERROR: FEEID_ChipIDs: feeid " << feeid << " is not valid" << endl;
        std::vector<int> chipids = {-1};
        return chipids;
    }        
}

vector<int> LayerStaveToFEEIDs(int layer = 0, int stave = 0)
{
    std::multimap<int, vector<int>> map_FEEIDtoLayerStave = FEEIDtoLayerStave();

    vector<int> test_LayerStave = {layer, stave};
    vector<int> matched_FEEID;
    matched_FEEID.clear();
    // Reverse search for FEEID from Layer Stave
    for (auto it = map_FEEIDtoLayerStave.rbegin(); it != map_FEEIDtoLayerStave.rend(); it++)
    {
        if (equal(it->second.begin(), it->second.end(), test_LayerStave.begin()))
        {
            matched_FEEID.push_back(it->first);
            continue;
        }
    }

    sort(matched_FEEID.begin(), matched_FEEID.end());
    // cout the matched FEEID
    // cout << "Layer " << test_LayerStave[0] << " Stave " << test_LayerStave[1] << " has FEEIDs: ";
    // for (int i = 0; i < matched_FEEID.size(); i++)
    // {
    //     cout << matched_FEEID[i] << " ";
    // }
    // cout << endl;

    return matched_FEEID;
}