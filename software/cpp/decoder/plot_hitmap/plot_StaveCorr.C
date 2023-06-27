#include <boost/bimap.hpp>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "./plotUtil.h"

using namespace std;

void GetNhitsStave_PerHB(const char *f_prefix, int layer, int stave) 
{
    vector<int> FEEIDs_layerstave = LayerStaveToFEEIDs(layer, stave);
    // print out the vector
    cout << "FEEIDs for Layer " << layer << " Stave " << stave << ": ";
    for (auto i : FEEIDs_layerstave)
        cout << i << " ";

    cout << endl;

    vector<vector<int>> NhitsPerHB_FEEID;

    for (size_t i = 0; i < FEEIDs_layerstave.size(); i++)
    {
        vector<int> NhitsPerHB;
        NhitsPerHB.clear();

        int feeid = FEEIDs_layerstave[i];
        TFile *f = new TFile(Form("/sphenix/user/hjheng/MVTXdecoder_PrivateCpp/felix-mvtx/software/cpp/decoder/fhrana_tree/%s/fhrana_%s_FEEID%d.root", f_prefix, f_prefix, feeid), "READ");
        TTree *t = (TTree *)f->Get("tree_fhrana");
        t->BuildIndex("event"); // Reference: https://root-forum.cern.ch/t/sort-ttree-entries/13138
        TTreeIndex *index = (TTreeIndex *)t->GetTreeIndex();
        int event, Nhits;
        vector<int> *ChipID_hit = 0;
        t->SetBranchAddress("event", &event);
        t->SetBranchAddress("Nhits", &Nhits);
        t->SetBranchAddress("ChipID_hit", &ChipID_hit);

        for (int i = 0; i < index->GetN(); i++)
        {
            Long64_t local = t->LoadTree(index->GetIndex()[i]);
            t->GetEntry(local);

            NhitsPerHB.push_back(Nhits);

            // cout << event << " " << ChipID_hit->size() << endl;
        }

        NhitsPerHB_FEEID.push_back(NhitsPerHB);
    }

    // get the minimum size of the vector
    int min_size = NhitsPerHB_FEEID[0].size();
    for (size_t i = 0; i < NhitsPerHB_FEEID.size(); i++)
    {
        if (NhitsPerHB_FEEID[i].size() < min_size)
            min_size = NhitsPerHB_FEEID[i].size();
    }

    cout << "min_size: " << min_size << endl;


    // print out the vector
    for (auto i : NhitsPerHB_FEEID)
    {
        cout << i.size() << endl;
    }
}

void plot_StaveCorr(const char *prefix)
{
    vector<int> StaveToCompare_1 = {0, 0};
    vector<int> StaveToCompare_2 = {0, 11};
    GetNhitsStave_PerHB(prefix, StaveToCompare_1[0], StaveToCompare_1[1]);
    GetNhitsStave_PerHB(prefix, StaveToCompare_2[0], StaveToCompare_2[1]);
    // LayerStaveToFEEIDs(StaveToCompare_1[0], StaveToCompare_1[1]);
    // LayerStaveToFEEIDs(StaveToCompare_2[0], StaveToCompare_2[1]);
}