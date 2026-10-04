#!/usr/bin/env python3
"""Assemble native CPU/console libraries and a gate-built memory map; no CPU emulation."""
from __future__ import annotations
import argparse
from pathlib import Path
import xml.etree.ElementTree as E
from generate_circuits import (ROOT, attr, circuit, component, constant, gate, invert,
                               loc, pin, port, project, serialize, sink, source, text, tunnel, wire)


def appearance(c, inputs, outputs, width=300):
    c.find("a[@name='appearance']").set("val", "custom")
    shape = E.SubElement(c, "appear")
    height = 40 * max(len(inputs), len(outputs)) + 20
    E.SubElement(shape, "rect", x="0", y="0", width=str(width), height=str(height), fill="#ffffff", stroke="#000000")
    for output, ports in ((False, inputs), (True, outputs)):
        for i, (name, bits) in enumerate(ports):
            y = 20 + i * 40
            x = width if output else 0
            px = 2200 if output else 100
            py = 160 + i * 60
            (sink if output else source)(c, px, py, name, bits)
            E.SubElement(shape, "circ-port", x=str(x), y=str(y), dir="out" if output else "in", pin=f"{px},{py}")
            E.SubElement(shape, "text", x=str(width-8 if output else 8), y=str(y+4), fill="#000000", **{"font-family":"SansSerif","font-size":"12","text-anchor":"end" if output else "start"}).text=name
    E.SubElement(shape, "circ-anchor", x=str(width), y="20", facing="east")


def instantiate(c, lib, name, x, y, definition, mapping):
    """Connect by native appearance metadata instead of duplicating pin geometry."""
    attrs = {} if lib is None else {"lib": str(lib)}
    E.SubElement(c, "comp", name=name, loc=loc(x,y), **attrs)
    shape = definition.find("appear")
    if shape is None:
        raise ValueError(f"{name} needs a stable custom appearance")
    anchor = shape.find("circ-anchor")
    ax, ay = int(anchor.get("x")), int(anchor.get("y"))
    pins = {}
    for node in definition.findall("comp[@name='Pin']"):
        a = {v.get("name"): v.get("val") for v in node.findall("a")}
        pins[node.get("loc").strip("()")] = (a["label"], int(a.get("width", "1")))
    for node in shape.findall("circ-port"):
        name, bits = pins[node.get("pin")]
        signal = mapping.get(name, name)
        xx = x + int(node.get("x")) + int(node.get("width", "0"))//2 - ax
        yy = y + int(node.get("y")) + int(node.get("height", "0"))//2 - ay
        port(c,xx,yy,signal,bits,"right" if node.get("dir")=="out" else "left")


def split(c, signal, bits, x, y, prefix):
    tunnel(c,x,y,signal,bits,"east")
    component(c,0,"Splitter",x,y,incoming=bits,fanout=bits,appear="right",facing="east",spacing=2)
    names=[]
    for i in range(bits):
        name=f"{prefix}{i}"
        wire(c,(x+20,y+10+20*i),(x+60,y+10+20*i))
        tunnel(c,x+60,y+10+20*i,name)
        names.append(name)
    return names


def join(c, signals, x, y, output):
    tunnel(c,x,y,output,len(signals),"east")
    component(c,0,"Splitter",x,y,incoming=len(signals),fanout=len(signals),appear="right",facing="east",spacing=2)
    for i,name in enumerate(signals):
        wire(c,(x+20,y+10+20*i),(x+60,y+10+20*i))
        tunnel(c,x+60,y+10+20*i,name)


def reduce_and(c, names, x, y, result):
    value=names[0]
    for i,name in enumerate(names[1:]):
        dest=result if i==len(names)-2 else f"{result}_{i}"
        gate(c,"AND",x+(i%4)*210,y+(i//4)*90,[value,name],dest)
        value=dest


def memory_map(p):
    c=circuit(p,"MemoryMap")
    appearance(c,[("Address",16),("Write",1),("Reset",1),("RamData",8),("RomData",8),("IoData",8)],
               [("BankAddress",12),("RamWrite",1),("ReadData",8),("IoSelect",1)])
    text(c,300,50,"Memory map / only gates and wiring; reserved addresses return FF")
    bits=split(c,"Address",16,330,140,"a")
    join(c,bits[:12],540,620,"BankAddress")
    for i in range(2,16):
        invert(c,550+(i%4)*170,140+(i//4)*70,f"a{i}",f"n{i}")
    reduce_and(c,[f"n{i}" for i in range(12,16)],1250,150,"RamSelect")
    reduce_and(c,[f"a{i}" for i in range(12,16)],1250,280,"RomSelect")
    reduce_and(c,[f"{'a' if 0xD010&(1<<i) else 'n'}{i}" for i in range(2,16)],700,900,"IoSelect")
    invert(c,1300,430,"Reset","NotReset")
    gate(c,"AND",1490,430,["Write","NotReset"],"SafeWrite")
    gate(c,"AND",1680,430,["SafeWrite","RamSelect"],"RamWrite")
    gate(c,"OR",1490,550,["RamSelect","RomSelect"],"MemorySelected")
    gate(c,"OR",1680,550,["MemorySelected","IoSelect"],"Selected")
    invert(c,1850,550,"Selected","Reserved")
    for i,(select,data) in enumerate((("RamSelect","RamData"),("RomSelect","RomData"),("IoSelect","IoData"),("Reserved","Ones"))):
        x,y=350+i*420,1450
        join(c,[select]*8,x,y,f"Mask{i}")
        gate(c,"AND",x+210,y+230,[f"Mask{i}",data],f"Bank{i}",8)
    constant(c,150,1420,255,8); tunnel(c,150,1420,"Ones",8)
    gate(c,"OR",750,1800,["Bank0","Bank1"],"MemoryData",8)
    gate(c,"OR",1250,1800,["Bank2","Bank3"],"OtherData",8)
    gate(c,"OR",1750,1800,["MemoryData","OtherData"],"ReadData",8)
    return c


def machine():
    from asm6502 import assemble
    cpu_path=ROOT/"circuits/generated/cpu6502.circ"
    terminal_path=ROOT/"circuits/generated/terminal.circ"
    cpu_project=E.parse(cpu_path).getroot()
    terminal_project=E.parse(terminal_path).getroot()
    cpu_name=cpu_project.find("main").get("name")
    cpu=cpu_project.find(f"circuit[@name='{cpu_name}']")
    console=terminal_project.find("circuit[@name='Apple1Console']")
    firmware=assemble((ROOT/"software/monitor/monitor.asm").read_text())
    rom=firmware.binary(0xf000,0x10000,fill=0xff)
    p=project("Bitwright")
    p.remove(next(node for node in p if node.tag is E.Comment))
    p.insert(0,E.Comment("GENERATED by tools/generate_machine.py; CPU, memory decode and terminal are native circuits."))
    E.SubElement(p,"lib",name="12",desc="file#generated/cpu6502.circ")
    E.SubElement(p,"lib",name="13",desc="file#generated/terminal.circ")
    c=circuit(p,"Bitwright")
    attr(c,simulationFrequency="65536.0")
    text(c,60,40,"BITWRIGHT / APPLE-1-INSPIRED GATE-BUILT COMPUTER")
    text(c,60,75,"Reset starts high: set it to 0, then enable ticks. Open the Console instance to type or load a .mon file.")
    text(c,60,105,"Assembly is compiled on the host; monitor firmware loads RAM; circuit CPU executes every instruction.")
    source(c,140,200,"Reset",initial=1)
    component(c,0,"Clock",140,270,highDuration=1,lowDuration=1,label="MachineClock")
    wire(c,(140,270),(180,270)); tunnel(c,180,270,"SysClock")
    constant(c,140,340,1);tunnel(c,140,340,"ONE")
    constant(c,140,370,0);tunnel(c,140,370,"ZERO")
    text(c,60,420,"Double-click CPU: inspect datapath and hardwired control.")
    text(c,60,450,"CPU storage is built from gates; console uses single-bit DFFs; bulk RAM/ROM are foundations.")
    text(c,60,480,"Documented 6502 encodings; functional timing. See coverage and measured compatibility limits.")
    instantiate(c,12,cpu_name,950,200,cpu,{"DataIn":"ReadData","DataOut":"WriteData","Halt":"Halted","IRQ":"ZERO","NMI":"ZERO"})
    instantiate(c,13,"Apple1Console",950,1150,console,{"DataIn":"WriteData","DataOut":"IoData"})
    text(c,560,990,"CONSOLE / enter this instance for keyboard, file loader and pixel screen")
    mm=memory_map(p)
    instantiate(c,None,"MemoryMap",460,650,mm,{})
    text(c,1160,520,"4 KiB RAM / programs, variables and stack")
    component(c,4,"RAM",1260,560,addrWidth=12,dataWidth=8,appearance="classic",label="PROGRAM_RAM",labelvisible=True,
              databus="bibus",enables="byte",asyncread=True,trigger="falling",clearpin=False)
    for dy,signal,width in ((10,"BankAddress",12),(50,"RamWrite",1),(70,"SysClock",1),(90,"WriteData",8)):
        port(c,1260,560+dy,signal,width)
    constant(c,1240,620,1);wire(c,(1240,620),(1260,620))
    port(c,1500,650,"RamData",8,"right")
    text(c,1160,800,"Firmware ROM / F000-FFFF; reset vector FFFC/FFFD")
    node=component(c,4,"ROM",1260,840,addrWidth=12,dataWidth=8,appearance="classic",label="PROGRAM_ROM",labelvisible=True)
    E.SubElement(node,"a",name="contents").text="addr/data: 12 8\n"+"\n".join(" ".join(f"{v:02x}" for v in rom[i:i+16]) for i in range(0,len(rom),16))
    port(c,1260,850,"BankAddress",12)
    port(c,1500,900,"RomData",8,"right")
    for i,(label,width) in enumerate((("PC",16),("A",8),("X",8),("Y",8),("SP",8),("P",8),("IR",8),("State",8),("Address",16),("WriteData",8),("ReadData",8),("Write",1),("Read",1),("Sync",1),("Fault",1))):
        sink(c,1900,170+i*60,label,width)
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    data=serialize(machine()); path=ROOT/"circuits/bitwright.circ"
    if args.check:
        if not path.is_file() or path.read_text()!=data:
            parser.exit(1,"Stale machine: run tools/generate_machine.py\n")
    else:
        path.write_text(data)
    print("Native machine is current." if args.check else "Generated native Bitwright machine.")

if __name__=="__main__":
    main()
