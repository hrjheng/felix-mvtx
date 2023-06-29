#include <boost/bimap.hpp>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "/sphenix/user/hjheng/TrackletAna/analysis/plot/sPHENIXStyle/sPhenixStyle.C"

#include "./plotUtil.h"

vector<int> GetNhitsStave_PerHB(const char *f_prefix, int layer, int stave)
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
        // t->BuildIndex("event"); // Reference: https://root-forum.cern.ch/t/sort-ttree-entries/13138
        t->BuildIndex("BCO");
        TTreeIndex *index = (TTreeIndex *)t->GetTreeIndex();
        int event, Nhits;
        uint64_t BCO;
        // vector<int> *ChipID_hit = 0;
        t->SetBranchAddress("event", &event);
        t->SetBranchAddress("BCO", &BCO);
        t->SetBranchAddress("Nhits", &Nhits);
        // t->SetBranchAddress("ChipID_hit", &ChipID_hit);

        for (int i = 0; i < index->GetN(); i++)
        {
            Long64_t local = t->LoadTree(index->GetIndex()[i]);
            t->GetEntry(local);

            // if (i < 10)
            //     cout << event << " " << BCO << " " << Nhits << endl;

            NhitsPerHB.push_back(Nhits);

            // cout << event << " " << ChipID_hit->size() << endl;
        }

        NhitsPerHB_FEEID.push_back(NhitsPerHB);
    }

    // get the minimum size of the vector (minimum number of HBs in this FEE ID)
    int min_size = NhitsPerHB_FEEID[0].size();
    for (size_t i = 0; i < NhitsPerHB_FEEID.size(); i++)
    {
        if (NhitsPerHB_FEEID[i].size() < min_size)
            min_size = NhitsPerHB_FEEID[i].size();
    }

    cout << "Minimum number of HBs in this stave = " << min_size << endl;

    // print out the vector
    for (auto i : NhitsPerHB_FEEID)
    {
        cout << i.size() << endl;
    }

    // sum up the Nhits for each event up to the minimum size
    vector<int> NhitsPerHB_sum;
    NhitsPerHB_sum.clear();
    for (size_t i = 0; i < min_size; i++)
    {
        int sum = 0;
        for (size_t j = 0; j < NhitsPerHB_FEEID.size(); j++)
        {
            sum += NhitsPerHB_FEEID[j][i];
        }
        NhitsPerHB_sum.push_back(sum);
    }

    // cout << NhitsPerHB_sum.size() << endl;

    return NhitsPerHB_sum;
}

void Draw_StaveCorr(TH2F *h, const char *XaxisTitle, const char *YaxisTitle, const char *legpos, const char *plotname)
{
    // Draw the 2D histogram
    TCanvas *c = new TCanvas("c", "c", 900, 700);
    c->cd();
    c->SetLogz();
    gPad->SetRightMargin(0.21);
    gPad->SetTopMargin(0.08);
    gPad->SetLeftMargin(0.15);
    gPad->SetBottomMargin(0.15);
    h->SetContour(1000);
    h->GetXaxis()->SetTitle(XaxisTitle);
    h->GetYaxis()->SetTitle(YaxisTitle);
    h->GetXaxis()->SetTitleSize(0.04);
    h->GetYaxis()->SetTitleSize(0.04);
    h->Draw("colz");

    gPad->Update();
    TPaletteAxis *palette = (TPaletteAxis *)h->GetListOfFunctions()->FindObject("palette");
    // the following lines move the palette. Choose the values you need for the position.
    palette->SetX1NDC(0.88);
    palette->SetX2NDC(0.93);
    gPad->Modified();
    gPad->Update();

    // Draw the legend, the position is set by the input argument (topright, topleft)
    float legx1, legx2, legy1, legy2;
    // compare the input argument legpos and set the position of the legend
    if (strcmp(legpos, "topright") == 0)
    {
        legx1 = 1 - gPad->GetRightMargin() - 0.43;
        legx2 = 1 - gPad->GetRightMargin() - 0.13;
        legy1 = 1 - gPad->GetTopMargin() - 0.16;
        legy2 = 1 - gPad->GetTopMargin() - 0.03;
        cout << legx1 << " " << legx2 << " " << legy1 << " " << legy2 << endl;
    }
    else if (strcmp(legpos, "topleft") == 0)
    {
        legx1 = gPad->GetLeftMargin() - 0.02;
        legx2 = gPad->GetLeftMargin() + 0.28;
        legy1 = 1 - gPad->GetTopMargin() - 0.16;
        legy2 = 1 - gPad->GetTopMargin() - 0.03;
        cout << legx1 << " " << legx2 << " " << legy1 << " " << legy2 << endl;
    }
    else
    {
        cout << "Legend position " << legpos << " is not supported!" << endl;
        return;
    }

    // Draw the legend
    TLegend *leg = new TLegend(legx1, legy1, legx2, legy2);
    leg->SetTextSize(0.045);
    leg->SetFillStyle(0);
    leg->AddEntry("", "#it{#bf{sPHENIX}} Internal", "");
    leg->AddEntry("", "Au+Au #sqrt{s_{NN}}=200 GeV", "");
    leg->Draw();

    c->SaveAs(Form("%s.png", plotname));
    c->SaveAs(Form("%s.pdf", plotname));
}

vector<vector<int>> StavesToCorrelate(int c)
{
    std::map<int, vector<vector<int>>> Map_StavesToCorrelateCase = {{0, {{0, 1}, {1, 3}}},
                                                                    {1, {{0, 2}, {0, 3}}},
                                                                    {2, {{0, 2}, {1, 3}}},
                                                                    {3, {{0, 3}, {0, 4}}},
                                                                    {4, {{0, 3}, {1, 4}}},
                                                                    {5, {{0, 3}, {2, 5}}},
                                                                    {6, {{0, 3}, {2, 6}}},
                                                                    {7, {{0, 5}, {0, 6}}},
                                                                    {8, {{0, 7}, {0, 8}}},
                                                                    {9, {{0, 9}, {0, 10}}},
                                                                    {10, {{0, 4}, {1, 5}}},
                                                                    {11, {{0, 4}, {1, 6}}},
                                                                    {12, {{0, 5}, {1, 7}}},
                                                                    {13, {{0, 4}, {2, 7}}},
                                                                    {14, {{0, 4}, {0, 10}}},
                                                                    {15, {{1, 6}, {2, 8}}},
                                                                    {16, {{1, 6}, {2, 7}}},
                                                                    {17, {{0, 8}, {1, 11}}},
                                                                    {18, {{1, 11}, {2, 14}}},
                                                                    {19, {{0, 10}, {1, 14}}},
                                                                    {20, {{0, 10}, {2, 18}}},
                                                                    {21, {{1, 4}, {2, 5}}},
                                                                    {22, {{0, 2}, {0, 8}}},
                                                                    {23, {{1, 14}, {2, 18}}}};


    return Map_StavesToCorrelateCase[c];
}

void plot_StaveCorr(const char *prefix)
{
    SetsPhenixStyle();
    gStyle->SetOptStat(0);
    TGaxis::SetMaxDigits(3);

    const char *plotpath = Form("./Correlation/%s/", prefix);
    system(Form("mkdir -p %s", plotpath));

    // Loop over the combinations in the StavesToCorrelate
    for (int i = 0; i < 23; i++)
    {
        plotpath = Form("./Correlation/%s/", prefix);

        vector<vector<int>> CorrelateStaves = StavesToCorrelate(i);
        // vector<int> GetNhitsStave_PerHB(const char *f_prefix, int layer, int stave)
        vector<int> NhitsPerHBPerStave_Stave1 = GetNhitsStave_PerHB(prefix, CorrelateStaves[0][0], CorrelateStaves[0][1]);
        vector<int> NhitsPerHBPerStave_Stave2 = GetNhitsStave_PerHB(prefix, CorrelateStaves[1][0], CorrelateStaves[1][1]);

        // get the minimum size of the vector
        int min_nHB = NhitsPerHBPerStave_Stave1.size();
        if (NhitsPerHBPerStave_Stave2.size() < min_nHB)
            min_nHB = NhitsPerHBPerStave_Stave2.size();

        // Fill the 2D histogram for the correlation
        TH2F *hM_NhitsPerHBPerStave_Stave1_Stave2 =
            new TH2F(Form("hM_NhitsPerHBPerStave_L%dS%d_L%dS%d", CorrelateStaves[0][0], CorrelateStaves[0][1], CorrelateStaves[1][0], CorrelateStaves[1][1]), Form("hM_NhitsPerHBPerStave_L%dS%d_L%dS%d", CorrelateStaves[0][0], CorrelateStaves[0][1], CorrelateStaves[1][0], CorrelateStaves[1][1]), 200, 0, 8000, 200, 0, 8000);

        for (size_t i = 0; i < min_nHB; i++)
        {
            hM_NhitsPerHBPerStave_Stave1_Stave2->Fill(NhitsPerHBPerStave_Stave1[i], NhitsPerHBPerStave_Stave2[i]);
        }

        Draw_StaveCorr(hM_NhitsPerHBPerStave_Stave1_Stave2, Form("Number of pixels over threshold per strobe (L%d S%d)", CorrelateStaves[0][0], CorrelateStaves[0][1]), Form("Number of pixels over threshold per strobe (L%d S%d)", CorrelateStaves[1][0], CorrelateStaves[1][1]), "topleft",
                       Form("%s/NhitsPerHBCorr_Layer%dStave%d_Layer%dStave%d", plotpath, CorrelateStaves[0][0], CorrelateStaves[0][1], CorrelateStaves[1][0], CorrelateStaves[1][1]));
    }

    // Nhits in staves in one quadrant: 3 staves in Layer0, 4 staves in Layer1, 5 staves in Layer2
}