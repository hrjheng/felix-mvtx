///////////////////////////////////////////////////////////////////////////////
// Title        : FX3 Controller Module
// Project      : Probecard
////////////////////////////////////////////////////////////////////////////////
// File         : usb_if_wrpr.sv
// Author       : Krzysztof Marek Sielewicz
// Company      : Warsaw University of Technology / CERN
// Author       : Matteo Lupi <matteo.lupi@cern.ch>
// Company      : CERN / Goethe Universitaet Frankfurt am Main
// Created      : 2015-12-02
// Last update  : 2016-03-04
// Platform     : Xilinx Vivado 2015.4
// Target       : Kintex-7
// Standard     : Verilog
////////////////////////////////////////////////////////////////////////////////
// Description: The usb interface wrapper file including FIFOs, fx_ctrl
////////////////////////////////////////////////////////////////////////////////

module usb_if_wrpr #(
                     parameter int GpifCtlWidth = 13, // GPIF II CTL bus width
                     parameter int GpifWidth = 32, // GPIF II bus width
                     parameter int WbDataWidth = 16, // data bus width
                     parameter int G_SEE_MITIGATION_TECHNIQUE = 0,
                     parameter int MISMATCH_EN = 1,
                     parameter int MISMATCH_REGISTERED = 1
                     )
   (
                      input                    clk_i, // clock input
                      input                    rst_i, // synchronous reset input

                      // wishbone bus signals
                      input                    wb_clk, // wishbone clock coming from usb_if
                      input                    wb_rst, // wishbone reset to be passed to the master

                      // Wishbone interface
                      input                    WB_LATCH_WORDS_COUNT_DP2, // latch words counter
                      input                    WB_RST_WORDS_COUNT_DP2, // rst words counter
                      output [WbDataWidth-1:0] WB_WORDS_COUNT_LSB_DP2, // counter output
                      output [WbDataWidth-1:0] WB_WORDS_COUNT_MSB_DP2, // counter output

                      input                    WB_LATCH_RDWORDS_COUNT_DP2, // latch rdwords counter
                      input                    WB_RST_RDWORDS_COUNT_DP2, // rst rdwords counter
                      output [WbDataWidth-1:0] WB_RDWORDS_COUNT_LSB_DP2, // counter output
                      output [WbDataWidth-1:0] WB_RDWORDS_COUNT_MSB_DP2, // counter output

                      input                    WB_LATCH_OVERFLOW_COUNT_DP2, // latch overflow counter
                      input                    WB_RST_OVERFLOW_COUNT_DP2, // rst overflow counter
                      output [WbDataWidth-1:0] WB_OVERFLOW_COUNT_DP2, // counter output

                      input                    WB_LATCH_FULL_COUNT_DP2, // latch overflow counter
                      input                    WB_RST_FULL_COUNT_DP2, // rst overflow counter
                      output [WbDataWidth-1:0] WB_FULL_COUNT_DP2, // counter output

                      input                    WB_LATCH_WORDS_COUNT_DP3, // latch words counter
                      input                    WB_RST_WORDS_COUNT_DP3, // rst words counter
                      output [WbDataWidth-1:0] WB_WORDS_COUNT_LSB_DP3, // counter output
                      output [WbDataWidth-1:0] WB_WORDS_COUNT_MSB_DP3, // counter output

                      input                    WB_LATCH_RDWORDS_COUNT_DP3, // latch rdwords counter
                      input                    WB_RST_RDWORDS_COUNT_DP3, // rst rdwords counter
                      output [WbDataWidth-1:0] WB_RDWORDS_COUNT_LSB_DP3, // counter output
                      output [WbDataWidth-1:0] WB_RDWORDS_COUNT_MSB_DP3, // counter output

                      input                    WB_LATCH_OVERFLOW_COUNT_DP3, // latch overflow counter
                      input                    WB_RST_OVERFLOW_COUNT_DP3, // rst overflow counter
                      output [WbDataWidth-1:0] WB_OVERFLOW_COUNT_DP3, // counter output

                      input                    WB_LATCH_FULL_COUNT_DP3, // latch overflow counter
                      input                    WB_RST_FULL_COUNT_DP3, // rst overflow counter
                      output [WbDataWidth-1:0] WB_FULL_COUNT_DP3, // counter output

                      // FX3 GPIFII Slave Fifo signals
                      input                    FLAGA_i, // FLAGAn input
                      input                    FLAGB_i, // FLAGBn input
                      input                    FLAGC_i, // FLAGCn input
                      input                    FLAGD_i, // FLAGDn input
                      output [1:0]             SLADDR_o, // slave endpoint address output
                      output                   SLOEn_o, // slave output enable
                      output                   SLCSn_o, // slave chip select output
                      output                   SLRDn_o, // slave read request output
                      output                   SLWRn_o, // slave write request output
                      output                   PKTENDn_o, // packet end output
                      input [GpifWidth-1:0]    DQ_i, // GPIFII DQ input (from the FX3)
                      output [GpifWidth-1:0]   DQ_o, // GPIFII DQ output (towards the FX3)

                      // data port 0 FIFO (wbmstr receives data from that FIFO)
                      input                    dp0_rdclk_i, // dataport 0 read clock
                      output [GpifWidth-1:0]   dp0_dt_o, // data port 0 data
                      output                   dp0_empty_o, // data port 0 empty
                      input                    dp0_rd_i, // data port 0 read

                      // data port 1 FIFO (wbmstr writes data to that FIFO)
                      input                    dp1_wrclk_i, // dataport 1 write clock
                      input [GpifWidth-1:0]    dp1_dt_i, // data port 1 data
                      output                   dp1_full_o, // data port 1 full
                      input                    dp1_wr_i, // data port 1 write

                      // DP2 interface (fx3_ctrl reades data from the DP2)
                      input                    clk_dp2_wr_i, // clock input for DP2 FIFO
                      input [GpifWidth-1:0]    dpo2_dti_i, // data port 2 data input
                      output                   dpo2_full_o, // data port 2 full output
                      output                   dpo2_almost_full_o, // data port 2 almost full output
                      input                    dpo2_wr_i, // data port 2 write input
                      output                   dpo2_empty_o, // data port 2 empty flag output
                      output                   dpo2_done_o, // data port 2 FSM done output
                      input                    dpo2_rst_wrclk_i, // DP2 rst

                      // DP3 interface (fx3_ctrl reades data from the DP3)
                      input                    clk_dp3_wr_i, // clock input for DP3 FIFO
                      input [GpifWidth-1:0]    dpo3_dti_i, // data port 3 data input
                      output                   dpo3_full_o, // data port 3 full output
                      output                   dpo3_almost_full_o, // data port 3 almost full output
                      input                    dpo3_wr_i, // data port 3 write input
                      output                   dpo3_empty_o, // data port 3 empty flag output
                      output                   dpo3_done_o, // data port 3 FSM done output
                      input                    dpo3_rst_wrclk_i // DP3 rst
                      );

   wire [GpifWidth-1:0]             dpi0_dti_w;
   wire [GpifWidth-1:0]             dpi0_dto_w;
   wire                             dpi0_full_w;
   wire                             dpi0_almost_full_w;
   wire                             dpi0_wr_w;
   wire                             dpi0_empty_w;
   wire                             dpi0_almost_empty_w;
   wire                             dpi0_rd_w;

   wire [GpifWidth-1:0]             dpo1_dti_w;
   wire [GpifWidth-1:0]             dpo1_dto_w;
   wire                             dpo1_full_w;
   wire                             dpo1_almost_full_w;
   wire                             dpo1_wr_w;
   wire                             dpo1_empty_w;
   wire                             dpo1_almost_empty_w;
   wire                             dpo1_rd_w;

   wire [GpifWidth-1:0]             s_dpo2_dto;
   wire                             s_dpo2_empty;
   assign        dpo2_empty_o = s_dpo2_empty;
   wire                             s_dpo2_almost_empty;
   wire                             s_dpo2_rd;

   wire [GpifWidth-1:0]             s_dpo3_dto;
   wire                              s_dpo3_empty;
   assign        dpo3_empty_o = s_dpo3_empty;
   wire                              s_dpo3_almost_empty;
   wire                              s_dpo3_rd;

////////////////////////////////////////////////////////////////////////////////
// FIFO for DP0
   xpm_fifo_async
     #(
       .FIFO_MEMORY_TYPE    ("block"),     //string; "auto", "block", or "distributed";
       .ECC_MODE            ("no_ecc"),    //string; "no_ecc" or "en_ecc";
       .RELATED_CLOCKS      (0),           //positive integer; 0 or 1
       .FIFO_WRITE_DEPTH    (1024),        //positive integer
       .WRITE_DATA_WIDTH    (32),          //positive integer, 0 or 1
       .WR_DATA_COUNT_WIDTH (10),          //positive integer
       .PROG_FULL_THRESH    (1021),        //positive integer
       .FULL_RESET_VALUE    (1),           //positive integer; 0 or 1
       .USE_ADV_FEATURES    ("0808"),      // Enable [12:8] = data_valid, almost_empty, rd_data_count, prog_empty, underflow,
                                           // [4:0] = wr_ack, almost_full, wr_data_count, prog_full, overflowalmost empty and almost full enabled
       .READ_MODE           ("std"),       //string; "std" or "fwft"
       .FIFO_READ_LATENCY   (2),           //positive integer
       .READ_DATA_WIDTH     (32),          //positive integer
       .RD_DATA_COUNT_WIDTH (10),          //positive integer
       .PROG_EMPTY_THRESH   (2),           //positive integer
       .DOUT_RESET_VALUE    ("0"),         //string; 0 or 1
       .CDC_SYNC_STAGES     (3),           //positive integer
       .WAKEUP_TIME         (0)            //positive integer; 0 or 2
       )
   fifo32x1024_DP0
     (
      .almost_empty         (dpi0_almost_empty_w),
      .almost_full          (dpi0_almost_full_w),
      .data_valid           (),
      .dbiterr              (),
      .dout                 (dp0_dt_o),
      .empty                (dp0_empty_o),
      .full                 (dpi0_full_w),
      .overflow             (),
      .prog_empty           (),
      .prog_full            (),
      .rd_data_count        (),
      .rd_rst_busy          (),
      .sbiterr              (),
      .underflow            (),
      .wr_ack               (),
      .wr_data_count        (),
      .wr_rst_busy          (),
      .din                  (dpi0_dti_w),
      .injectdbiterr        (1'b0),
      .injectsbiterr        (1'b0),
      .rd_clk               (dp0_rdclk_i),
      .rd_en                (dp0_rd_i),
      .rst                  (rst_i),
      .sleep                (1'b0),
      .wr_clk               (clk_i),
      .wr_en                (dpi0_wr_w)
      );

   //////////////////////////////////////////////
   // Assertions
   // synthesis translate_off
   //////////////////////////////////////////////
   always @(posedge clk_i)
     begin
        assert(!((dpi0_full_w == 1'b1) && (dpi0_wr_w == 1'b1))) else $warning("DP0 Fifo write while full");
     end

   always @(posedge dp0_rdclk_i)
     begin
        assert(!((dp0_empty_o == 1'b1) && (dp0_rd_i == 1'b1))) else $warning("DP0 Fifo read while empty");
     end

   // synthesis translate_on

////////////////////////////////////////////////////////////////////////////////
// FIFO for DP1
   xpm_fifo_async
     #(
       .FIFO_MEMORY_TYPE    ("block"),     //string; "auto", "block", or "distributed";
       .ECC_MODE            ("no_ecc"),    //string; "no_ecc" or "en_ecc";
       .RELATED_CLOCKS      (0),           //positive integer; 0 or 1
       .FIFO_WRITE_DEPTH    (1024),        //positive integer
       .WRITE_DATA_WIDTH    (32),          //positive integer, 0 or 1
       .WR_DATA_COUNT_WIDTH (10),          //positive integer
       .PROG_FULL_THRESH    (1021),        //positive integer
       .FULL_RESET_VALUE    (1),           //positive integer; 0 or 1
       .USE_ADV_FEATURES    ("0808"),      // Enable [12:8] = data_valid, almost_empty, rd_data_count, prog_empty, underflow,
                                           // [4:0] = wr_ack, almost_full, wr_data_count, prog_full, overflowalmost empty and almost full enabled
       .READ_MODE           ("std"),       //string; "std" or "fwft"
       .FIFO_READ_LATENCY   (2),           //positive integer
       .READ_DATA_WIDTH     (32),          //positive integer
       .RD_DATA_COUNT_WIDTH (10),          //positive integer
       .PROG_EMPTY_THRESH   (2),           //positive integer
       .DOUT_RESET_VALUE    ("0"),         //string; 0 or 1
       .CDC_SYNC_STAGES     (3),           //positive integer
       .WAKEUP_TIME         (0)            //positive integer; 0 or 2
       )
   fifo32x1024_DP1
     (
      .almost_empty         (dpo1_almost_empty_w),
      .almost_full          (dpo1_almost_full_w),
      .data_valid           (),
      .dbiterr              (),
      .dout                 (dpo1_dto_w),
      .empty                (dpo1_empty_w),
      .full                 (dp1_full_o),
      .overflow             (),
      .prog_empty           (),
      .prog_full            (),
      .rd_data_count        (),
      .rd_rst_busy          (),
      .sbiterr              (),
      .underflow            (),
      .wr_ack               (),
      .wr_data_count        (),
      .wr_rst_busy          (),
      .din                  (dp1_dt_i),
      .injectdbiterr        (1'b0),
      .injectsbiterr        (1'b0),
      .rd_clk               (clk_i),
      .rd_en                (dpo1_rd_w),
      .rst                  (rst_i),
      .sleep                (1'b0),
      .wr_clk               (dp1_wrclk_i),
      .wr_en                (dp1_wr_i)
      );

   //////////////////////////////////////////////
   // Assertions
   // synthesis translate_off
   //////////////////////////////////////////////
   always @(posedge dp1_wrclk_i)
     begin
        assert(!((dp1_full_o == 1'b1) && (dp1_wr_i == 1'b1))) else $warning("DP1 Fifo write while full");
     end

   always @(posedge clk_i)
     begin
        assert(!((dpo1_empty_w == 1'b1) && (dpo1_rd_w == 1'b1))) else $warning("DP1 Fifo read while empty");
     end

   // synthesis translate_on

////////////////////////////////////////////////////////////////////////////////
// FIFO for DP2
   DP23_fifo #(.WbDataWidth(WbDataWidth),
               .GpifWidth(GpifWidth))
   INST_DP23_fifo_DP2
     (
      .rst_i          (rst_i),
      //WB
      .WB_CLK         (wb_clk),
      .WB_RST         (wb_rst),

      .LATCH_WORDS_COUNT_I(WB_LATCH_WORDS_COUNT_DP2),
      .RST_WORDS_COUNT_I(WB_RST_WORDS_COUNT_DP2),
      .WORDS_COUNT_MSB_O(WB_WORDS_COUNT_MSB_DP2),
      .WORDS_COUNT_LSB_O(WB_WORDS_COUNT_LSB_DP2),

      .LATCH_RDWORDS_COUNT_I(WB_LATCH_RDWORDS_COUNT_DP2),
      .RST_RDWORDS_COUNT_I(WB_RST_RDWORDS_COUNT_DP2),
      .RDWORDS_COUNT_MSB_O(WB_RDWORDS_COUNT_MSB_DP2),
      .RDWORDS_COUNT_LSB_O(WB_RDWORDS_COUNT_LSB_DP2),

      .LATCH_OVERFLOW_COUNT_I(WB_LATCH_OVERFLOW_COUNT_DP2),
      .RST_OVERFLOW_COUNT_I  (WB_RST_OVERFLOW_COUNT_DP2),
      .OVERFLOW_COUNT_O      (WB_OVERFLOW_COUNT_DP2),

      .LATCH_FULL_COUNT_I(WB_LATCH_FULL_COUNT_DP2),
      .RST_FULL_COUNT_I  (WB_RST_FULL_COUNT_DP2),
      .FULL_COUNT_O      (WB_FULL_COUNT_DP2),
      // wrclk
      .clk_dp_wr_i       (clk_dp2_wr_i),
      .dpo_rst_wrclk_i   (dpo2_rst_wrclk_i),
      .dpo_wr_i          (dpo2_wr_i),
      .dpo_dti_i         (dpo2_dti_i),
      .dpo_full_o        (dpo2_full_o),
      .dpo_almost_full_o (dpo2_almost_full_o),
      // rdclk
      .clk_rd_i          (clk_i),
      .dpo_rst_rdclk_i   (rst_i),
      .dpo_rd_i          (s_dpo2_rd),
      .dpo_dto_o         (s_dpo2_dto),
      .dpo_empty_o       (s_dpo2_empty),
      .dpo_almost_empty_o(s_dpo2_almost_empty)
      /*AUTOINST*/);

   // synthesis translate_off
   ////////////////////
   // logging module //
   ////////////////////
   int                          f2;

   initial begin
      // get file_handler
      f2 = $fopen("fifodump_DP2", "w");
      if (!f2)
        $display("Could not open \"fifodump_dp2\"");
      else begin
         for (integer i = 0; i<500000; i++) begin
            @(posedge clk_dp2_wr_i);
            if (dpo2_wr_i) begin
               // write to file
               $fwrite(f2, "%h\n", dpo2_dti_i);
            end
         end
         $fclose(f2);
      end
   end
   // synthesis translate_on

////////////////////////////////////////////////////////////////////////////////
// FIFO for DP3
   DP23_fifo #(.WbDataWidth(WbDataWidth),
               .GpifWidth(GpifWidth))
   INST_DP23_fifo_DP3(
                      // Outputs

                      .rst_i          (rst_i),
                      //WB
                      .WB_CLK         (wb_clk),
                      .WB_RST         (wb_rst),

                      .LATCH_WORDS_COUNT_I(WB_LATCH_WORDS_COUNT_DP3),
                      .RST_WORDS_COUNT_I(WB_RST_WORDS_COUNT_DP3),
                      .WORDS_COUNT_MSB_O(WB_WORDS_COUNT_MSB_DP3),
                      .WORDS_COUNT_LSB_O(WB_WORDS_COUNT_LSB_DP3),

                      .LATCH_RDWORDS_COUNT_I(WB_LATCH_RDWORDS_COUNT_DP3),
                      .RST_RDWORDS_COUNT_I(WB_RST_RDWORDS_COUNT_DP3),
                      .RDWORDS_COUNT_MSB_O(WB_RDWORDS_COUNT_MSB_DP3),
                      .RDWORDS_COUNT_LSB_O(WB_RDWORDS_COUNT_LSB_DP3),

                      .LATCH_OVERFLOW_COUNT_I(WB_LATCH_OVERFLOW_COUNT_DP3),
                      .RST_OVERFLOW_COUNT_I (WB_RST_OVERFLOW_COUNT_DP3),
                      .OVERFLOW_COUNT_O     (WB_OVERFLOW_COUNT_DP3),

                      .LATCH_FULL_COUNT_I(WB_LATCH_FULL_COUNT_DP3),
                      .RST_FULL_COUNT_I (WB_RST_FULL_COUNT_DP3),
                      .FULL_COUNT_O     (WB_FULL_COUNT_DP3),

                      // wrclk
                      .clk_dp_wr_i       (clk_dp3_wr_i),
                      .dpo_rst_wrclk_i   (dpo3_rst_wrclk_i),
                      .dpo_wr_i          (dpo3_wr_i),
                      .dpo_dti_i         (dpo3_dti_i),
                      .dpo_full_o        (dpo3_full_o),
                      .dpo_almost_full_o (dpo3_almost_full_o),

                      // rdclk
                      .clk_rd_i          (clk_i),
                      .dpo_rst_rdclk_i   (rst_i),
                      .dpo_rd_i          (s_dpo3_rd),
                      .dpo_dto_o         (s_dpo3_dto),
                      .dpo_empty_o       (s_dpo3_empty),
                      .dpo_almost_empty_o(s_dpo3_almost_empty)
                      /*AUTOINST*/);

   // synthesis translate_off
   ////////////////////
   // logging module //
   ////////////////////
   int                          f3;

   initial begin
 // get file_handler
      f3 = $fopen("fifodump_DP3", "w");
      if (!f3)
        $display("Could not open \"fifodump_dp3\"");
      else begin
         for (integer i = 0; i<500000; i++) begin
            @(posedge clk_dp3_wr_i);
            if (dpo3_wr_i) begin
               // write to file
               $fwrite(f3, "%h\n", dpo3_dti_i);
            end
         end
         $fclose(f3);
      end
   end
   // synthesis translate_on

////////////////////////////////////////////////////////////////////////////////
// FX3 controller
fx3_ctrl #(.GpifWidth(GpifWidth),
           .GpifCtlWidth(GpifCtlWidth))
   fx3_ctrl (
  .clk_i              (clk_i),
  .rst_i              (rst_i),
  // FX3 GPIF II BUS
  .FLAGA_i            (FLAGA_i),
  .FLAGB_i            (FLAGB_i),
  .FLAGC_i            (FLAGC_i),
  .FLAGD_i            (FLAGD_i),
  .SLADDR_o           (SLADDR_o),
  .SLOEn_o            (SLOEn_o),
  .SLCSn_o            (SLCSn_o),
  .SLRDn_o            (SLRDn_o),
  .SLWRn_o            (SLWRn_o),
  .PKTENDn_o          (PKTENDn_o),
  .DQ_i               (DQ_i),
  .DQ_o               (DQ_o),
  // DP0
  .dp0_dt_o             (dpi0_dti_w),
  .dp0_full_i           (dpi0_full_w),
  .dp0_almost_full_i    (dpi0_almost_full_w),
  .dp0_wr_o             (dpi0_wr_w),
  // DP1
  .dpo1_dt_i            (dpo1_dto_w),
  .dpo1_empty_i         (dpo1_empty_w),
  .dpo1_almost_empty_i  (dpo1_almost_empty_w),
  .dpo1_rd_o            (dpo1_rd_w),
  // DP2
  .dpo2_dt_i            (s_dpo2_dto),
  .dpo2_empty_i         (s_dpo2_empty),
  .dpo2_almost_empty_i  (s_dpo2_almost_empty),
  .dpo2_rd_o            (s_dpo2_rd),
  .dpo2_done_o          (dpo2_done_o),
  // DP3
  .dpo3_dt_i            (s_dpo3_dto),
  .dpo3_empty_i         (s_dpo3_empty),
  .dpo3_almost_empty_i  (s_dpo3_almost_empty),
  .dpo3_rd_o            (s_dpo3_rd),
  .dpo3_done_o          (dpo3_done_o)
);

endmodule
