#include <fstream>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "/sphenix/user/hjheng/TrackletAna/analysis/plot/sPHENIXStyle/sPhenixStyle.C"

#include "plotUtil.h"

void Draw_Hitmap(TH2F *hm, int feeid, int layer, int stave, int chip, TString outname)
{
    TGaxis::SetMaxDigits(6);

    gStyle->SetOptStat(0);

    TCanvas *c = new TCanvas("c", "c", 1500, 800);
    c->cd();
    gPad->SetRightMargin(0.14);
    gPad->SetTopMargin(0.08);
    gPad->SetLeftMargin(0.15);
    gPad->SetBottomMargin(0.15);

    c->SetLogz();
    hm->GetXaxis()->SetTitle("Column ID");
    hm->GetYaxis()->SetTitle("Row ID");
    hm->GetZaxis()->SetRangeUser(0.999999, hm->GetMaximum());
    hm->GetZaxis()->SetMoreLogLabels();
    hm->SetLineColor(0);
    hm->SetContour(1000);
    hm->Draw("colz");

    TText *t = new TText(0.86, 0.93, Form("FEE ID:%d, Layer:%d, Stave:%d, Chip:%d", feeid, layer, stave, chip));
    t->SetNDC();
    t->SetTextAlign(kVAlignBottom + kHAlignRight);
    t->SetTextSize(0.04);
    t->Draw("same");
    c->SaveAs(Form("%s.png", outname.Data()));
    c->SaveAs(Form("%s.pdf", outname.Data()));
}

void hitmap(const char *f_prefix, int feeid, int EvtNum)
{
    int layer = static_cast<int>((static_cast<uint32_t>(feeid) & 0x7000) >> 12);
    int gbt_channel = static_cast<int>((static_cast<uint32_t>(feeid) & 0x0300) >> 8);
    int stave = static_cast<int>(static_cast<uint32_t>(feeid) & 0x003f);

    vector<TH2F *> hM_colrowID_ChipID;
    hM_colrowID_ChipID.clear();
    for (int i = 0; i < 3; i++)
    {
        hM_colrowID_ChipID.push_back(new TH2F(Form("hM_colrowID_ChipIDmod%d", i), Form("hM_colrowID_ChipIDmod%d", i), 1024, 0, 1024, 512, 0, 512));
    }

    TFile *f = new TFile(Form("/sphenix/user/hjheng/MVTXdecoder_PrivateCpp/felix-mvtx/software/cpp/decoder/fhrana_tree/%s/fhrana_%s_FEEID%d.root", f_prefix, f_prefix, feeid), "READ");
    TTree *t = (TTree *)f->Get("tree_fhrana");

    t->BuildIndex("event"); // Reference: https://root-forum.cern.ch/t/sort-ttree-entries/13138
    TTreeIndex *index = (TTreeIndex *)t->GetTreeIndex();
    int event;
    vector<int> *ColumnID_hit = 0, *RowID_hit = 0, *ChipID_hit = 0;
    t->SetBranchAddress("event", &event);
    t->SetBranchAddress("ColumnID_hit", &ColumnID_hit);
    t->SetBranchAddress("RowID_hit", &RowID_hit);
    t->SetBranchAddress("ChipID_hit", &ChipID_hit);

    vector<int> unique_chipID = FEEID_ChipIDs(feeid);
    vector<int> count_Nhits_PerChip = {0, 0, 0};

    // int EventToPlot = 19185 + 1;
    system(Form("mkdir -p ./ColRowMap/%s/Event%d/", f_prefix, EvtNum));

    if (EvtNum == -1) // When the specified EvtNum is -1, run first 1000 HBs
    {
        // for (int i = 0; i < index->GetN(); i++)
        for (int i = 0; i < 1000000; i++)
        {
            Long64_t local = t->LoadTree(index->GetIndex()[i]);
            t->GetEntry(local);

            // Reset the count_Nhits_PerChip
            count_Nhits_PerChip = {0, 0, 0};

            for (size_t ihit = 0; ihit < ColumnID_hit->size(); ihit++)
            {
                int chipID_idx = ChipID_hit->at(ihit) % 3;
                count_Nhits_PerChip[chipID_idx]++;
                hM_colrowID_ChipID[chipID_idx]->Fill(ColumnID_hit->at(ihit), RowID_hit->at(ihit));
            }
        }
    }
    else // When the specified EvtNum is not -1, run only the specified event
    {
        if (EvtNum < t->GetEntries())
        {
            for (int i = EvtNum; i < EvtNum + 1; i++)
            {
                Long64_t local = t->LoadTree(index->GetIndex()[i]);
                t->GetEntry(local);

                // Reset the count_Nhits_PerChip
                count_Nhits_PerChip = {0, 0, 0};

                for (size_t ihit = 0; ihit < ColumnID_hit->size(); ihit++)
                {
                    int chipID_idx = ChipID_hit->at(ihit) % 3;
                    count_Nhits_PerChip[chipID_idx]++;
                    hM_colrowID_ChipID[chipID_idx]->Fill(ColumnID_hit->at(ihit), RowID_hit->at(ihit));
                }
            }
        }
    }

    for (size_t i = 0; i < unique_chipID.size(); i++)
    {
        cout << "unique_chipID.at(" << i << ")=" << unique_chipID.at(i) << " Nhits on this chip=" << count_Nhits_PerChip.at(i) << endl;
        Draw_Hitmap(hM_colrowID_ChipID[i], feeid, layer, stave, unique_chipID.at(i), Form("./ColRowMap/%s/Event%d/FEEID%d_Layer%d_Stave%d_ChipID%d", f_prefix, EvtNum, feeid, layer, stave, unique_chipID.at(i)));
    }

    f->Close();

    // Save histograms to root file
    TFile *fout = new TFile(Form("./ColRowMap/%s/Event%d/HitmapHist_Layer%d_Stave%d_Chip%dto%d.root", f_prefix, EvtNum, layer, stave, unique_chipID[0], unique_chipID[unique_chipID.size() - 1]), "RECREATE");
    fout->cd();
    for (size_t i = 0; i < hM_colrowID_ChipID.size(); i++)
    {
        hM_colrowID_ChipID[i]->Write();
    }
    fout->Close();

    for (size_t i = 0; i < hM_colrowID_ChipID.size(); i++)
    {
        delete hM_colrowID_ChipID[i];
    }
}

void Draw_Nhits_PerChip(const char *f_prefix, int feeid)
{
    TGaxis::SetMaxDigits(3);

    int layer = static_cast<int>((static_cast<uint32_t>(feeid) & 0x7000) >> 12);
    int gbt_channel = static_cast<int>((static_cast<uint32_t>(feeid) & 0x0300) >> 8);
    int stave = static_cast<int>(static_cast<uint32_t>(feeid) & 0x003f);

    vector<TH1F *> hM_Nhits_ChipID;
    hM_Nhits_ChipID.clear();
    for (int i = 0; i < 3; i++)
    {
        hM_Nhits_ChipID.push_back(new TH1F(Form("hM_Nhits_ChipIDmod%d", i), Form("hM_Nhits_ChipIDmod%d", i), 200, 0, 20000));
    }

    vector<int> unique_chipID = FEEID_ChipIDs(feeid);
    vector<int> count_Nhits_PerChip = {0, 0, 0};

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

        count_Nhits_PerChip = {0, 0, 0};

        for (size_t ihit = 0; ihit < ChipID_hit->size(); ihit++)
        {
            int chipID_idx = ChipID_hit->at(ihit) % 3;
            count_Nhits_PerChip[chipID_idx]++;
        }

        for (size_t i = 0; i < unique_chipID.size(); i++)
        {
            hM_Nhits_ChipID[i]->Fill(count_Nhits_PerChip[i]);
        }
    }

    // Draw all the histograms and save to pdf
    TCanvas *c = new TCanvas("c", "c", 800, 600);
    c->SetLogy();
    for (size_t i = 0; i < unique_chipID.size(); i++)
    {
        c->cd();
        gPad->SetTopMargin(0.1);
        gPad->SetRightMargin(0.12);
        hM_Nhits_ChipID[i]->GetXaxis()->SetTitle("Number of pixels over threshold");
        hM_Nhits_ChipID[i]->GetYaxis()->SetTitle("Entries");
        hM_Nhits_ChipID[i]->Draw("HIST");

        TText *txt = new TText(1 - gPad->GetRightMargin(), 1 - gPad->GetTopMargin() + 0.01, Form("Layer:%d, Stave:%d, Chip:%d, Number of HBs:%lld", layer, stave, unique_chipID[i], t->GetEntries()));
        txt->SetNDC();
        txt->SetTextAlign(kVAlignBottom + kHAlignRight);
        txt->Draw("same");

        c->SaveAs(Form("./ColRowMap/%s/FEEID%d_Layer%d_Stave%d_ChipID%d_Nhits.png", f_prefix, feeid, layer, stave, unique_chipID.at(i)));
        c->SaveAs(Form("./ColRowMap/%s/FEEID%d_Layer%d_Stave%d_ChipID%d_Nhits.pdf", f_prefix, feeid, layer, stave, unique_chipID.at(i)));
    }
}

void Draw_StaveHitmap(vector<TH2F *> hists, int layer, int stave, const char *outname)
{
    TGaxis::SetMaxDigits(6);
    // Get the maximum of the histograms
    float max = 0;
    for (int i = 0; i < 9; i++)
    {
        cout << "histogram " << i << " has maximum " << hists[i]->GetMaximum() << endl;
        if (hists[i]->GetMaximum() > max)
        {
            max = hists[i]->GetMaximum();
        }
    }

    // Divide the TVanvas into 1x9 pads, then draw the histograms in each pad
    TCanvas *c = new TCanvas("c", "c", 1500 * 1.3 * 9, 1500);
    c->SetBottomMargin(0.01);
    c->SetFillColor(0);
    c->SetFrameFillStyle(0);
    gStyle->SetLineWidth(10);

    int Nx = 9;
    TPad *pad[Nx];
    // Margins
    float lMargin = 0.02;
    float rMargin = 0.025;
    float bMargin = 0.15;
    float tMargin = 0.1;

    // Setup Pad layout:
    float hSpacing = 0.0;
    float hStep = (1. - lMargin - rMargin - (Nx - 1) * hSpacing) / Nx;
    float hposl, hposr, hmarl, hmarr, hfactor;
    for (int i = 0; i < Nx; i++)
    {
        if (i == 0)
        {
            hposl = 0.0;
            hposr = lMargin + hStep;
            hfactor = hposr - hposl;
            hmarl = lMargin / hfactor;
            hmarr = 0.0;
        }
        else if (i == Nx - 1)
        {
            hposl = hposr + hSpacing;
            hposr = hposl + hStep + rMargin;
            hfactor = hposr - hposl;
            hmarl = 0.0;
            hmarr = rMargin / (hposr - hposl);
        }
        else
        {
            hposl = hposr + hSpacing;
            hposr = hposl + hStep;
            hfactor = hposr - hposl;
            hmarl = 0.0;
            hmarr = 0.0;
        }
        c->cd(0);
        const char *name = Form("pad_%i_%i", i, 0);
        pad[i] = new TPad(Form("pad_%i", i), "", hposl, 0.1, hposr, 0.9);
        pad[i]->SetLeftMargin(hmarl);
        pad[i]->SetRightMargin(hmarr);
        // pad[i]->SetFrameBorderMode(2);
        pad[i]->SetFillColor(0);
        pad[i]->SetFrameFillStyle(0);
        // pad[i]->SetBorderMode(0);
        // pad[i]->SetBorderSize(1);
        pad[i]->SetFrameLineWidth(5);
        pad[i]->Draw();
    }

    for (int i = 0; i < Nx; i++)
    {
        c->cd(0);

        pad[i]->Draw();
        pad[i]->cd();
        pad[i]->SetLogz();

        if (i < 8)
        {
            if (i == 0)
            {
                hists[i]->GetYaxis()->SetTitle("Row ID");
                hists[i]->GetYaxis()->SetTitleSize(0.07);
                hists[i]->GetYaxis()->SetTitleOffset(1.2);
            }
            else
            {
                hists[i]->GetYaxis()->SetTitle("");
            }

            // if (i > 0)
            // {
            //     hists[i]->GetXaxis()->ChangeLabel(1,-1,0,-1,-1,-1,"");
            // }

            // hists[i]->GetXaxis()->ChangeLabel(-1,-1,0,-1,-1,-1,"");

            hists[i]->GetXaxis()->SetTitle("");
            hists[i]->GetZaxis()->SetRangeUser(0.999, max);
            hists[i]->SetContour(1000);
            hists[i]->Draw("colz");
            hists[i]->SetDrawOption("col");

            TText *t = new TText(1 - pad[i]->GetRightMargin(), 1 - pad[i]->GetTopMargin() + 0.01, Form("Layer:%d, Stave:%d, Chip:%d, # of pixels over threshold:%d, ", layer, stave, i, int(hists[i]->GetEntries())));
            t->SetNDC();
            t->SetTextAlign(kVAlignBottom + kHAlignRight);
            t->SetTextSize(0.06);
            t->Draw("same");
        }
        else
        {
            hists[i]->GetXaxis()->SetTitle("Column ID");
            hists[i]->GetYaxis()->SetTitle("Row ID");

            hists[i]->GetXaxis()->SetTitleSize(0.07);
            hists[i]->GetXaxis()->SetTitleOffset(1.2);

            hists[i]->GetZaxis()->SetTitleSize(0.07);
            hists[i]->GetZaxis()->SetTitleOffset(1.1);

            // hists[i]->GetXaxis()->ChangeLabel(1,-1,0,-1,-1,-1,"");

            hists[i]->GetZaxis()->SetRangeUser(0.999, max);
            hists[i]->Draw("colz");

            TH2F *dummy = new TH2F("dummy", "", 1024, 0, 1024, 512, 0, 512);
            dummy->SetBinContent(1, 1, 1E-10);
            dummy->GetZaxis()->SetRangeUser(0.999, max);
            dummy->GetZaxis()->SetMoreLogLabels();
            // dummy->GetZaxis()->SetTitle("Number of pixels over threshold");
            // dummy->GetZaxis()->SetTitleSize(0.06);
            dummy->SetContour(1000);
            dummy->Draw("colz");
            pad[i]->Update();
            pad[i]->Modified();
            TPaletteAxis *palette = (TPaletteAxis *)dummy->GetListOfFunctions()->FindObject("palette");
            palette->SetX1NDC(1 - pad[i]->GetRightMargin() + 0.01);
            palette->SetX2NDC(1 - pad[i]->GetRightMargin() + 0.07);
            palette->SetY1NDC(pad[i]->GetBottomMargin());
            palette->SetY2NDC(1 - pad[i]->GetTopMargin());
            pad[i]->Modified();
            pad[i]->Update();
            pad[i]->RedrawAxis();

            hists[i]->Draw("colsame");

            TText *t = new TText(1 - pad[i]->GetRightMargin(), 1 - pad[i]->GetTopMargin() + 0.01, Form("Layer:%d, Stave:%d, Chip:%d, # of pixels over threshold:%d", layer, stave, i, int(hists[i]->GetEntries())));
            t->SetNDC();
            t->SetTextAlign(kVAlignBottom + kHAlignRight);
            t->SetTextSize(0.06);
            t->Draw("same");
        }
    }
    c->SaveAs(Form("%s.png", outname));
    gStyle->SetLineScalePS(0.1);
    c->SaveAs(Form("%s.eps", outname));
    // c->SaveAs(Form("%s.pdf", outname));
}

void plot_hitmap(const char *prefix)
{
    SetsPhenixStyle();
    gStyle->SetPalette(kRainBow);

    const char *plotpath = Form("./ColRowMap/%s", prefix);
    system(Form("mkdir -p %s", plotpath));

    vector<vector<int>> FEEIDs = {{0, 256, 512, 4099, 4355, 4611, 8198, 8199, 8454, 8455, 8710, 8711, 1, 257, 513, 4100, 4356, 4612, 8200, 8201, 8456, 8457, 8712, 8713}, {2, 258, 514, 4101, 4102, 4357, 4358, 4613, 4614, 8202, 8458, 8714, 3, 259, 515, 4103, 4359, 4615, 8203, 8204, 8459, 8460, 8715, 8716},
                                  {4, 260, 516, 4104, 4105, 4360, 4361, 4616, 4617, 8205, 8461, 8717, 5, 261, 517, 4106, 4362, 4618, 8206, 8207, 8462, 8463, 8718, 8719}, {6, 262, 518, 4107, 4363, 4619, 8208, 8209, 8464, 8465, 8720, 8721, 7, 263, 519, 4108, 4364, 4620, 8210, 8211, 8466, 8467, 8722, 8723},
                                  {8, 264, 520, 4109, 4110, 4365, 4366, 4621, 4622, 8192, 8448, 8704, 9, 265, 521, 4111, 4367, 4623, 8193, 8194, 8449, 8450, 8705, 8706}, {10, 266, 522, 4096, 4097, 4352, 4353, 4608, 4609, 8195, 8451, 8707, 11, 267, 523, 4098, 4354, 4610, 8196, 8197, 8452, 8453, 8708, 8709}};

    // For now, only plot Stave L0_00
    // vector<int> EvtNum_ToPlot = {19, 436, 777, 1195, 1224, 1464, 1671, 1874, 2028, 2623, 2751, 4383, 6868, 16968, 17354, 19185, 23043, 32233, 45329, 55265, 55648, 67755, 79011, 91444, 93916, 95152, 144345, 168805, 194408}; // Run 14142, Yellow-beam only
    // vector<int> EvtNum_ToPlot = {16368, 19857, 31270, 46683, 55888, 98186, 123304, 161576, 219668, 313699}; // Run 14137, Blue-beam only, Test-run configuration
    vector<int> EvtNum_ToPlot = {2162, 4560, 8060, 18786, 32397, 51800, 52125, 52126, 89680, 109681, 335567, 378530}; // Run 14138, Blue-beam only, Data-run configuration
    // vector<int> EvtNum_ToPlot = {-1}; // Run 14144, No beam

    for (size_t iflx = 0; iflx < FEEIDs.size(); iflx++)
    {
        cout << "FELIX " << iflx << endl;
        for (size_t i = 0; i < FEEIDs[iflx].size(); i++)
        {
            // For now, only plot Stave L0_00
            // if (iflx != 0)
            //     continue;

            // if (FEEIDs[iflx][i] != 0 && FEEIDs[iflx][i] != 256 && FEEIDs[iflx][i] != 512)
            //     continue;

            try
            {
                for (size_t ievt = 0; ievt < EvtNum_ToPlot.size(); ievt++)
                {
                    hitmap(prefix, FEEIDs[iflx][i], EvtNum_ToPlot[ievt]);
                }

                Draw_Nhits_PerChip(prefix, FEEIDs[iflx][i]);
            }
            catch (const std::exception &e)
            {
                std::cerr << e.what() << '\n';
                continue;
            }
        }
    }

    // plot the hitmap for the whole stave
    vector<int> NStaves_Layer = {12, 16, 20};
    for (size_t l = 0; l < NStaves_Layer.size(); l++)
    {
        for (int s = 0; s < NStaves_Layer[l]; s++)
        {
            // For now, only plot Stave L0_00
            // if (l != 0 || s != 0)
            //     continue;

            for (size_t ievt = 0; ievt < EvtNum_ToPlot.size(); ievt++)
            {
                vector<TString> histfiles = {Form("./ColRowMap/%s/Event%d/HitmapHist_Layer%zu_Stave%d_Chip0to2.root", prefix, EvtNum_ToPlot[ievt], l, s), Form("./ColRowMap/%s/Event%d/HitmapHist_Layer%zu_Stave%d_Chip3to5.root", prefix, EvtNum_ToPlot[ievt], l, s),
                                             Form("./ColRowMap/%s/Event%d/HitmapHist_Layer%zu_Stave%d_Chip6to8.root", prefix, EvtNum_ToPlot[ievt], l, s)};
                // get the histograms from the files
                vector<TH2F *> hM_hitmap_chips;
                for (size_t i = 0; i < histfiles.size(); i++)
                {
                    TFile *f = new TFile(histfiles[i], "READ");
                    for (size_t j = 0; j < 3; j++)
                    {
                        TH2F *h = (TH2F *)f->Get(Form("hM_colrowID_ChipIDmod%zu", j));
                        h->SetName(Form("hM_colrowID_ChipID%zu", 3 * i + j));
                        hM_hitmap_chips.push_back(h);
                    }
                }

                Draw_StaveHitmap(hM_hitmap_chips, l, s, Form("./ColRowMap/%s/Event%d/HitmapStave_Layer%zu_Stave%d", prefix, EvtNum_ToPlot[ievt], l, s));
            }
        }
    }
}