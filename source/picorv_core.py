#!/usr/bin/env python3
#
#  PicoRV -- A Small and Extensible RISC-V Processor
#
#  Copyright (C) 2019  Claire Wolf <claire@symbioticeda.com>
#
#  Permission to use, copy, modify, and/or distribute this software for any
#  purpose with or without fee is hereby granted, provided that the above
#  copyright notice and this permission notice appear in all copies.
#
#  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
#  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
#  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
#  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
#  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
#  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

def csrs_cfg():
    add_csr("mcycle", 0xb00)
    add_csr("minstret", 0xb02)
    add_csr("mcycleh", 0xb80)
    add_csr("minstreth", 0xb82)

    add_csr_post_vlog("""
        {csr_mcycleh, csr_mcycle} = {csr_mcycleh, csr_mcycle} + 1;
        {csr_minstreth, csr_minstret} = {csr_minstreth, csr_minstret} + (pcpi_valid && pcpi_ready_ctrl);
    """)

def components_cfg():
    add_component("picorv_exec", "exec", br=True, params={"CPI": "CPI"})
    add_component("picorv_ldst", "ldst", mem=True, awb=True)

#####################################################################

print("""// generated by picorv_core.py
module picorv_core #(
  parameter integer CPI = 2,
  parameter integer CSRS = 1,
  parameter integer XLEN = 32,
  parameter integer ILEN = 32,
  parameter integer IALIGN = 16,
  parameter integer RPORTS = 3,
  parameter [XLEN-1:0] SPINIT = 1
) (
  // control
  input            clock,
  input            reset,
  input [XLEN-1:0] rvec,

  // memory interface
  output            mem_valid,
  input             mem_ready,
  output            mem_insn,
  output [XLEN-1:0] mem_addr,
  input  [    31:0] mem_rdata,
  output [    31:0] mem_wdata,
  output [     3:0] mem_wstrb,

  // decode
  output            decode_valid,
  output [ILEN-1:0] decode_insn,
  output [    15:0] decode_prefix,

  // pcpi
  output            pcpi_valid,
  output [ILEN-1:0] pcpi_insn,
  output [    15:0] pcpi_prefix,
  output [XLEN-1:0] pcpi_pc,
  output            pcpi_rs1_valid,
  output [XLEN-1:0] pcpi_rs1_data,
  output            pcpi_rs2_valid,
  output [XLEN-1:0] pcpi_rs2_data,
  output            pcpi_rs3_valid,
  output [XLEN-1:0] pcpi_rs3_data,
  input             pcpi_ready,
  output            pcpi_wb_valid,
  input             pcpi_wb_async,
  input             pcpi_wb_write,
  input  [XLEN-1:0] pcpi_wb_data,
  input             pcpi_br_enable,
  input  [XLEN-1:0] pcpi_br_nextpc,

  // async writeback
  input             awb_valid,
  output            awb_ready,
  input  [     4:0] awb_addr,
  input  [XLEN-1:0] awb_data
);
  wire pcpi_ready_ctrl;
""")

#####################################################################

csrs = []
csraddrs = dict()
csrrstvals = dict()
csrs_pre_vlog_snippets = []
csrs_post_vlog_snippets = []

print("  wire            mem_reqst_csrs = 0;")
print("  wire            mem_grant_csrs;")
print("  wire            mem_valid_csrs = 0;")
print("  wire            mem_ready_csrs;")
print("  wire [XLEN-1:0] mem_addr_csrs = 0;")
print("  wire [    31:0] mem_wdata_csrs = 0;")
print("  wire [     3:0] mem_wstrb_csrs = 0;")

print("  wire            pcpi_ready_csrs;")
print("  wire            pcpi_wb_write_csrs;")
print("  wire            pcpi_wb_async_csrs = 0;")
print("  wire [XLEN-1:0] pcpi_wb_data_csrs;")
print("  wire            pcpi_br_enable_csrs = 0;")
print("  wire [XLEN-1:0] pcpi_br_nextpc_csrs = 0;")

print("  wire            awb_valid_csrs = 0;")
print("  wire            awb_ready_csrs;")
print("  wire [     4:0] awb_addr_csrs = 0;")
print("  wire [XLEN-1:0] awb_data_csrs = 0;")

print("  wire csrinsn_valid = pcpi_valid && pcpi_insn[6:0] == 7'b 1110011 && pcpi_insn[13:12] != 2'b 00 && (pcpi_rs1_valid || pcpi_insn[14]);")
print("  wire [11:0] csrinsn_addr = pcpi_insn[31:20];")
print("  wire [XLEN-1:0] csrinsn_data = pcpi_insn[14] ? pcpi_insn[19:15] : pcpi_rs1_data;")
print("  wire [1:0] csrinsn_op = pcpi_insn[13:12];")
print("  reg csrinsn_ready;")
print("  reg [XLEN-1:0] csrinsn_out;")
print("  wire [XLEN-1:0] csrinsn_clr = 0;")
print("  wire [XLEN-1:0] csrinsn_set = 0;")

def add_csr(name, addr, rstval="0"):
    csrs.append(name)
    csraddrs[name] = addr
    csrrstvals[name] = rstval
    print("  reg  [XLEN-1:0] csr_%s;" % name)
    print("  reg  [XLEN-1:0] csr_%s_reg;" % name)
    print("  wire [XLEN-1:0] csr_%s_clr = 0;" % name)
    print("  wire [XLEN-1:0] csr_%s_set = 0;" % name)
    print("  always @(posedge clock) csr_%s_reg <= reset ? %s : csr_%s;" % (name, rstval, name))

def add_csr_pre_vlog(code):
    csrs_pre_vlog_snippets.append(code)

def add_csr_post_vlog(code):
    csrs_post_vlog_snippets.append(code)

csrs_cfg()

print("  always @* begin")
print("    csrinsn_ready = 0;")
print("    csrinsn_out = 0;")

for n in csrs:
    print("    csr_%s = csr_%s_reg;" % (n, n))

for c in csrs_pre_vlog_snippets:
    print(c)

print("    if (csrinsn_valid) begin")
print("      case (csrinsn_addr)")

for n in csrs:
    print("        12'h %03x: begin csrinsn_ready = 1; csrinsn_out = csr_%s; csr_%s = (csr_%s & ~csrinsn_clr) | csrinsn_set; end" % (csraddrs[n], n, n, n))

print("      endcase")
print("    end else begin")

for n in csrs:
    print("      csr_%s = (csr_%s & ~csr_%s_clr) | csr_%s_set;" % (n, n, n, n))

print("    end")

for c in csrs_post_vlog_snippets:
    print(c)

print("    if (!CSRS) begin")
for n in csrs:
    print("      csr_%s = %s;" % (n, csrrstvals[n]))
print("    end")

print("  end")

print("  assign pcpi_ready_csrs = csrinsn_ready && pcpi_valid && pcpi_wb_valid;")
print("  assign pcpi_wb_write_csrs = pcpi_ready_csrs;")
print("  assign pcpi_wb_data_csrs = pcpi_ready_csrs ? csrinsn_out : 0;")

#####################################################################

components = ["csrs"]

def add_component(modname, instname, params=dict(), ports=dict(), csrs=set(), mem=False, awb=False, br=False):
    components.append(instname)

    print("  wire            mem_reqst_%s;" % instname)
    print("  wire            mem_grant_%s;" % instname)
    print("  wire            mem_valid_%s;" % instname)
    print("  wire            mem_ready_%s;" % instname)
    print("  wire [XLEN-1:0] mem_addr_%s;" % instname)
    print("  wire [    31:0] mem_wdata_%s;" % instname)
    print("  wire [     3:0] mem_wstrb_%s;" % instname)

    print("  wire            pcpi_ready_%s;" % instname)
    print("  wire            pcpi_wb_write_%s;" % instname)
    print("  wire            pcpi_wb_async_%s;" % instname)
    print("  wire [XLEN-1:0] pcpi_wb_data_%s;" % instname)
    print("  wire            pcpi_br_enable_%s;" % instname)
    print("  wire [XLEN-1:0] pcpi_br_nextpc_%s;" % instname)

    print("  wire            awb_valid_%s;" % instname)
    print("  wire            awb_ready_%s;" % instname)
    print("  wire [     4:0] awb_addr_%s;" % instname)
    print("  wire [XLEN-1:0] awb_data_%s;" % instname)

    print("  %s #(" % modname);
    print("    .XLEN(XLEN)")
    print("  , .ILEN(ILEN)")
    for key, val in params.items():
        print("  , .%s(%s)" % (key, val))
    print("  ) %s (" % instname)
    print("    .clock          (clock         )")
    print("  , .reset          (reset         )")
    if mem:
        print("  , .mem_reqst (mem_reqst_%s)" % instname)
        print("  , .mem_grant (mem_grant_%s)" % instname)
        print("  , .mem_valid (mem_valid_%s)" % instname)
        print("  , .mem_ready (mem_ready_%s)" % instname)
        print("  , .mem_addr  (mem_addr_%s )" % instname)
        print("  , .mem_rdata (mem_rdata)")
        print("  , .mem_wdata (mem_wdata_%s )" % instname)
        print("  , .mem_wstrb (mem_wstrb_%s )" % instname)
    print("  , .decode_valid   (decode_valid  )")
    print("  , .decode_insn    (decode_insn   )")
    print("  , .decode_prefix  (decode_prefix )")
    print("  , .pcpi_valid     (pcpi_valid    )")
    print("  , .pcpi_insn      (pcpi_insn     )")
    print("  , .pcpi_prefix    (pcpi_prefix   )")
    print("  , .pcpi_pc        (pcpi_pc       )")
    print("  , .pcpi_rs1_valid (pcpi_rs1_valid)")
    print("  , .pcpi_rs1_data  (pcpi_rs1_data )")
    print("  , .pcpi_rs2_valid (pcpi_rs2_valid)")
    print("  , .pcpi_rs2_data  (pcpi_rs2_data )")
    print("  , .pcpi_rs3_valid (pcpi_rs3_valid)")
    print("  , .pcpi_rs3_data  (pcpi_rs3_data )")
    print("  , .pcpi_ready     (pcpi_ready_%s    )" % instname)
    print("  , .pcpi_wb_valid  (pcpi_wb_valid    )")
    print("  , .pcpi_wb_write  (pcpi_wb_write_%s )" % instname)
    print("  , .pcpi_wb_data   (pcpi_wb_data_%s  )" % instname)
    if br:
        print("  , .pcpi_br_enable (pcpi_br_enable_%s)" % instname)
        print("  , .pcpi_br_nextpc (pcpi_br_nextpc_%s)" % instname)
    if awb:
        print("  , .pcpi_wb_async  (pcpi_wb_async_%s )" % instname)
        print("  , .awb_valid      (awb_valid_%s)" % instname)
        print("  , .awb_ready      (awb_ready_%s)" % instname)
        print("  , .awb_addr       (awb_addr_%s)" % instname)
        print("  , .awb_data       (awb_data_%s)" % instname)
    for key, val in ports.items():
        print("  , .%s(%s)" % (key, val))
    print("  );")

    if not mem:
        print("  assign mem_reqst_%s = 0;" % instname)
        print("  assign mem_valid_%s = 0;" % instname)
        print("  assign mem_addr_%s = 0;" % instname)
        print("  assign mem_wdata_%s = 0;" % instname)
        print("  assign mem_wstrb_%s = 0;" % instname)

    if not br:
        print("  assign pcpi_br_enable_%s = 0;" % instname)
        print("  assign pcpi_br_nextpc_%s = 0;" % instname)

    if not awb:
        print("  assign pcpi_wb_async_%s = 0;" % instname)
        print("  assign awb_valid_%s = 0;" % instname)
        print("  assign awb_addr_%s = 0;" % instname)
        print("  assign awb_data_%s = 0;" % instname)

components_cfg()

#####################################################################

print("  wire            mem_valid_ctrl;")
print("  wire            mem_ready_ctrl;")
print("  wire [XLEN-1:0] mem_addr_ctrl;")
print("  wire [XLEN-1:0] mem_wdata_ctrl = 0;")
print("  wire      [3:0] mem_wstrb_ctrl = 0;")

print("  wire            awb_valid_ctrl;")
print("  wire            awb_ready_ctrl;")
print("  wire [     4:0] awb_addr_ctrl;")
print("  wire [XLEN-1:0] awb_data_ctrl;")

for n in ["ctrl"] + components:
    print("  reg arb_mem_%s_reg;" % n)

p = []
q = list(components)
for n in components:
    print("  wire arb_mem_%s = %s;" % (n, " && ".join(["!arb_mem_%s" % m for m in p] +
            ["mem_reqst_%s" % n] + ["!(mem_reqst_%s && arb_mem_%s_reg)" % (m, m) for m in q[1:]])))
    print("  assign mem_ready_%s = arb_mem_%s && mem_ready;" % (n, n))
    print("  assign mem_grant_%s = arb_mem_%s;" % (n, n))
    print("  always @(posedge clock) arb_mem_%s_reg <= reset ? 0 : arb_mem_%s;" % (n, n))
    p.append(n)
    q = q[1:]

print("  wire arb_mem_ctrl = mem_valid_ctrl && %s;" % (" && ".join(["!arb_mem_%s" % m for m in p])))
print("  assign mem_ready_ctrl = arb_mem_ctrl && mem_ready;")
print("  always @(posedge clock) arb_mem_ctrl_reg <= reset ? 0 : arb_mem_ctrl;")

p = []
for n in components:
    print("  wire arb_awb_%s = !awb_valid && %s;" % (n, " && ".join(["awb_valid_%s" % n] + ["!awb_valid_%s" % m for m in p])))
    print("  assign awb_ready_%s = arb_awb_%s && awb_ready_ctrl;" % (n, n))
    p.append(n)

for n in ["valid", "addr", "wdata", "wstrb"]:
    print("  assign mem_%s = %s;" % (n, " | ".join(["(arb_mem_%s ? mem_%s_%s : 0)" % (m, n, m) for m in ["ctrl"] + components])))
print("  assign mem_insn = arb_mem_ctrl;")

for n in ["valid", "addr", "data"]:
    print("  assign awb_%s_ctrl = awb_valid ? awb_%s : %s;" % (n, n, " | ".join(["(arb_awb_%s ? awb_%s_%s : 0)" % (m, n, m) for m in components])))
print("  assign awb_ready = awb_valid && awb_ready_ctrl;")

print("assign pcpi_ready_ctrl = pcpi_ready|%s;" % "|".join(["pcpi_ready_%s" % n for n in components]))

print("  picorv_ctrl #(");
print("    .XLEN(XLEN)")
print("  , .ILEN(ILEN)")
print("  , .IALIGN(IALIGN)")
print("  , .RPORTS(RPORTS)")
print("  , .SPINIT(SPINIT)")
print("  ) ctrl (")
print("    .clock          (clock         )")
print("  , .reset          (reset         )")
print("  , .rvec           (rvec          )")
print("  , .mem_valid (mem_valid_ctrl)")
print("  , .mem_ready (mem_ready_ctrl)")
print("  , .mem_addr  (mem_addr_ctrl )")
print("  , .mem_rdata (mem_rdata)")
print("  , .decode_valid  (decode_valid  )")
print("  , .decode_insn   (decode_insn   )")
print("  , .decode_prefix (decode_prefix )")
print("  , .pcpi_valid    (pcpi_valid    )")
print("  , .pcpi_insn     (pcpi_insn     )")
print("  , .pcpi_prefix   (pcpi_prefix   )")
print("  , .pcpi_pc       (pcpi_pc       )")
print("  , .pcpi_rs1_valid(pcpi_rs1_valid)")
print("  , .pcpi_rs1_data (pcpi_rs1_data )")
print("  , .pcpi_rs2_valid(pcpi_rs2_valid)")
print("  , .pcpi_rs2_data (pcpi_rs2_data )")
print("  , .pcpi_rs3_valid(pcpi_rs3_valid)")
print("  , .pcpi_rs3_data (pcpi_rs3_data )")
print("  , .pcpi_ready    (pcpi_ready_ctrl)")
print("  , .pcpi_wb_valid (pcpi_wb_valid)")
print("  , .pcpi_wb_async (pcpi_wb_async|%s)" % "|".join(["pcpi_wb_async_%s" % n for n in components]))
print("  , .pcpi_wb_write (pcpi_wb_write|%s)" % "|".join(["pcpi_wb_write_%s" % n for n in components]))
print("  , .pcpi_wb_data  (pcpi_wb_data|%s)" % "|".join(["pcpi_wb_data_%s" % n for n in components]))
print("  , .pcpi_br_enable(pcpi_br_enable|%s)" % "|".join(["pcpi_br_enable_%s" % n for n in components]))
print("  , .pcpi_br_nextpc(pcpi_br_nextpc|%s)" % "|".join(["pcpi_br_nextpc_%s" % n for n in components]))
print("  , .awb_valid(awb_valid_ctrl)")
print("  , .awb_ready(awb_ready_ctrl)")
print("  , .awb_addr (awb_addr_ctrl)")
print("  , .awb_data (awb_data_ctrl)")
print("  );")

print("endmodule")