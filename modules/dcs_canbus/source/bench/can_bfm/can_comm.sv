//-----------------------------------------------------------------------------
// Title      : CAN Bus Communication module interface
// Project    : ALICE ITS WP10
//-----------------------------------------------------------------------------
// File       : can_comm.sv
// Author     : Simon Voigt Nesboe  <svn@hvl.no>
// Company    : Western Norway University of Applied Sciences
// Created    : 2018-09-27
// Last update: 2020-04-03
// Platform   : Kintex 7 / Simulation
// Standard   : System Verilog
//-----------------------------------------------------------------------------
// Description: Interface with python scripts via sockets
//
//              The fifo contain one "raw can frames" per line,
//              ie. arbitration ID and payload data.
//              Remote frames are not used, and only standard canbus frames are
//              used (11-bit arb ID, represented with 2 bytes in fifo file).
//
//              It is assumed that every transaction is initiated by python,
//              and that there's a response to each frame from the firmware.
//              The class monitors the socket for packets
//              and uses the CANbus BFM to write this to the CAN bus signals,
//              so it can be received by the firmware.
//              It then uses the CANbus BFM to read/wait for a frame/response
//              from the firmware, and puts the response package into the
//              socket
//-----------------------------------------------------------------------------
// Copyright (c)   2019
//-----------------------------------------------------------------------------
// Revisions  :
// Date        Version  Author        Description
// 2018-09-27  1.0      simon	        Created
// 2020-04-03  2.0      AV            Changed to socket comm
//-----------------------------------------------------------------------------

import sock::*;

class CanComm;
  parameter real pollrate_us = 1;

  can_bfm m_can_bfm;

  // CAN controller needs a couple of microseconds after reset to be able
  // to generate sample point and sync on to incoming CAN messages.
  // Since there is no way for this class to know when reset was issued,
  // the necessary delay is added before the first package is sent,
  // which is indicated by this variable
  bit          m_first_byte = 1'b0;

  chandle m_sock_h; // Handle for socket
  const string port = "32229"; // Port used for TCP connection
  bit    m_isAlive = 0;

  const string s_timeout = "TIMEOUT";
  const string s_crc_error = "CRC_ERROR";
  const string s_arb_lost = "ARB_LOST";
  const string s_ack_missing = "ACK_MISSING";

  function new(ref can_bfm can, input bit allowNoConnection);
    this.m_can_bfm = can;
    sock_init();

    // Connect
`ifdef UNIX
    this.m_sock_h = sock_open({"unix://@cancomm"}, NON_BLOCKING);
`else
    this.m_sock_h = sock_open({"tcp://localhost:", port}, NON_BLOCKING);
`endif
    if(this.m_sock_h == null) begin
      if (!allowNoConnection) begin
        $error("CanComm::Error connecting to python server");
        sock_shutdown();
        $finish();
      end
      else begin
        this.m_can_bfm.disableAllTasks();
        $display("CanComm::All CAN tasks off");
        return;
      end
    end
    this.m_isAlive = 1;
  endfunction : new

  function bit readFromPython(ref can_package_t can_package);
    const string line = sock_readln(this.m_sock_h);
    if(line.len() == 0 || line == "EXIT") begin
      sock_shutdown();
      $finish();
    end
    else if(line != "NOP") begin
      handleReadData(line, can_package);
      readFromPython = 1;
    end
    else
      readFromPython = 0;
  endfunction : readFromPython

  // Each line in the fifo file contains one CAN frame
  // The lines are written in ascii hex format, each line contains at least 2 bytes,
  // where the first 2 bytes is the arbitration ID (represented with 16-bits,
  // although only 11-bits for standard CAN frame), and up to 8 bytes of payload.
  function void handleReadData(const ref string line, ref can_package_t can_package);
    const int line_length = line.len();
    const string arb_id_str = line.substr(0,3);

    assert (line_length >= 4)
    else $fatal(1, "%0t can_comm:: can_fifo_fp contained line with %d characters, should be minimum 4 (2 bytes).", $time, line_length);
    assert (line_length % 2 == 0)
    else $fatal(1, "%0t can_comm:: can_fifo_fp contained line with odd number of characters %d.", $time, line_length);

    // 2 bytes for ID + 8 bytes max CAN payload = 10 bytes
    // 10 byte x 2 characters per byte = 20 bytes max for a CAN frame
    // (Note that the HLP protocol only uses up to 4 bytes payload)
    assert (line_length <= 20)
    else $fatal(1, "%0t can_comm:: can_fifo_fp contained line with %d characters, too many for can frame.", $time, line_length);

    can_package.arb_id = arb_id_str.atohex();
    can_package.extended_id = 0;
    can_package.remote_frame = 0;

    // 2 characters per byte. 2 bytes for arb id, rest is payload
    can_package.data_length = (line_length-4)/2;

    // Start at byte 2, after arb id, where payload data starts
    for (int byte_num = 2; byte_num < line_length/2; byte_num++) begin
      const string sub = line.substr(2*byte_num, 2*byte_num+1);
      can_package.data[byte_num-2] = sub.atohex();
    end
  endfunction : handleReadData

  function void writeDataToPython(const ref can_package_t can_package);
    string s_word;
    $sformat(s_word, "%04H", can_package.arb_id);
    for(int i = 0; i < can_package.data_length; i++) begin
      $sformat(s_word, "%s%02H", s_word, can_package.data[i]);
    end
    writeToPython(s_word);
  endfunction : writeDataToPython

  function void writeToPython(const ref string s_word);
    if (!sock_writeln(this.m_sock_h, s_word)) begin
      sock_shutdown();
      $finish();
    end
  endfunction : writeToPython

  task can_comm();

    forever begin

      can_package_t can_pkg_to_sim;
      can_package_t can_pkg_from_sim;

      if(readFromPython(can_pkg_to_sim)) begin
        bit arb_lost;
        bit ack_received;
        bit timeout;
        bit crc_error;

        // Add delay before transmitting first package, in case CAN controller
        // was just reset and needs some time before it can sync on a CAN package
        if(!m_first_byte) begin
          #10us m_first_byte = 1'b1;
        end

        // Print package to write to CAN interface
        if(can_pkg_to_sim.arb_id[2:0] == 3'b010) begin
          // Write command
          bit [31:0] can_payload = {>>{can_pkg_to_sim.data[3:0]}};
          bit [15:0] hlp_reg_data = {>>{can_pkg_to_sim.data[3:2]}};
          $display("%0t can_comm::WR FIFO-->CAN: %3x %8x  Wr Cmd  - ID:%d    M:%d A:%d D:%d", $time,
            can_pkg_to_sim.arb_id,
            can_payload,
            can_pkg_to_sim.arb_id[10:3],
            can_pkg_to_sim.data[0],
            can_pkg_to_sim.data[1],
            hlp_reg_data);
        end else if(can_pkg_to_sim.arb_id[2:0] == 3'b100) begin
          // Read command
          bit [15:0] can_payload = {>>{can_pkg_to_sim.data[1:0]}};
          $display("%0t can_comm::WR FIFO-->CAN: %3x %4x      Rd Cmd  - ID:%d    M:%d A:%d", $time,
            can_pkg_to_sim.arb_id,
            can_payload,
            can_pkg_to_sim.arb_id[10:3],
            can_pkg_to_sim.data[0],
            can_pkg_to_sim.data[1]);
        end else begin
          bit [31:0] can_payload = {>>{can_pkg_to_sim.data[3:0]}};
          $display("%0t can_comm::WR FIFO-->CAN: %3x %8x  Unknown type", $time,
            can_pkg_to_sim.arb_id, can_payload);
        end

        // Send CAN HLP read command/request
        m_can_bfm.can_write(can_pkg_to_sim, arb_lost, ack_received);

        // Check for errors
        if(arb_lost) begin
          writeToPython(s_arb_lost);
          $warning("%0t can_comm::WR FIFO-->CAN: ARB_LOST", $time);
        end else if(!ack_received) begin
          writeToPython(s_ack_missing);
          $warning("%0t can_comm::WR FIFO-->CAN: ACK_MISSING", $time);
        end else begin
          // Read the response from the RU firmware
          // This code assumes that all CAN bus frames are initiated from the python script,
          // and each frame from the python script gets exactly one reponse from the firmware
          m_can_bfm.can_read(can_pkg_from_sim, timeout, crc_error);

          // Write reponse data to fifo file, or TIMEOUT/CRC_ERROR if receiving response failed
          if(timeout) begin
            writeToPython(s_timeout);
            $warning("%0t can_comm::RD CAN-->FIFO: TIMEOUT", $time);
          end else if(crc_error) begin
            writeToPython(s_crc_error);
            $warning("%0t can_comm::RD CAN-->FIFO: CRC_ERROR", $time);
          end else begin
            writeDataToPython(can_pkg_from_sim);

            // Print package read from CAN interface
            if(can_pkg_from_sim.arb_id[2:0] == 3'b011) begin
              // Write response
              bit [31:0] can_payload = {>>{can_pkg_from_sim.data[3:0]}};
              bit [15:0] hlp_reg_data = {>>{can_pkg_from_sim.data[3:2]}};
              $display("%0t can_comm::RD CAN-->FIFO: %3x %8x  Wr Resp - ID:%d    M:%d A:%d D:%d", $time,
                can_pkg_from_sim.arb_id,
                can_payload,
                can_pkg_from_sim.arb_id[10:3],
                can_pkg_from_sim.data[0],
                can_pkg_from_sim.data[1],
                hlp_reg_data);
            end else if(can_pkg_from_sim.arb_id[2:0] == 3'b101) begin
              // Read response
              bit [31:0] can_payload = {>>{can_pkg_from_sim.data[3:0]}};
              bit [15:0] hlp_reg_data = {>>{can_pkg_from_sim.data[3:2]}};
              $display("%0t can_comm::RD CAN-->FIFO: %3x %8x  Rd Resp - ID:%d    M:%d A:%d D:%d", $time,
                can_pkg_from_sim.arb_id,
                can_payload,
                can_pkg_from_sim.arb_id[10:3],
                can_pkg_from_sim.data[0],
                can_pkg_from_sim.data[1],
                hlp_reg_data);
                  end else begin // if (can_pkg_from_sim.arb_id[2:0] == 3'b101)
              bit [31:0] can_payload = {>>{can_pkg_from_sim.data[3:0]}};
              $display("%0t can_comm::RD CAN-->FIFO: %3x %8x  Unknown type", $time,
                can_pkg_from_sim.arb_id, can_payload);
            end
          end
        end
      end
      #(pollrate_us*1us);
    end
  endtask : can_comm

  task start_comm();
    fork
      can_comm();
    join
  endtask : start_comm
endclass : CanComm
