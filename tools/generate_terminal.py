#!/usr/bin/env python3
"""Generate gate-built Apple-1-style console. Java handles ASCII and raw pixels only."""
from __future__ import annotations
import argparse
from pathlib import Path
import xml.etree.ElementTree as E
from generate_circuits import attr, circuit, component, constant, dff, loc, pin, port, project, serialize, sink, source, text, tunnel, wire
ROOT=Path(__file__).resolve().parents[1]

class Builder:
    def __init__(self,p,name,ins,outs):
        self.p=p;self.c=circuit(p,name);self.i=0;self.n=0;self.name=name
        self.ins=ins;self.outs=outs
        for j,(label,width) in enumerate(ins):source(self.c,100,120+j*50,label,width)
        for j,(label,width) in enumerate(outs):sink(self.c,10500,120+j*50,label,width)
        self.c.find("a[@name='appearance']").set('val','custom')
        a=E.SubElement(self.c,'appear');h=max(len(ins),len(outs))*30+30
        E.SubElement(a,'rect',x='0',y='-20',width='240',height=str(h),fill='#ffffff',stroke='#222222',**{'stroke-width':'2'})
        E.SubElement(a,'text',x='120',y='-4',fill='#222222',**{'font-family':'SansSerif','font-size':'11','text-anchor':'middle'}).text=name
        for side,items,x,px in [('in',ins,0,100),('out',outs,240,10500)]:
            for j,(label,_) in enumerate(items):
                E.SubElement(a,'circ-port',x=str(x),y=str(j*30+10),dir=side,pin=f'{px},{120+j*50}')
                E.SubElement(a,'text',x=str(8 if side=='in' else 232),y=str(j*30+14),fill='#222222',**{'font-family':'SansSerif','font-size':'10','text-anchor':'start' if side=='in' else 'end'}).text=label
        E.SubElement(a,'circ-anchor',x='240',y='10',facing='east')
        text(self.c,70,50,name+' / gates, wiring, explicit single-bit flip-flops; bulk RAM and font ROM only')
    def fresh(self,s='n'):
        self.n+=1;return f'{s}_{self.n}'
    def pos(self,height=190):
        # Keep each block in a separate horizontal band. No hidden crossing junctions.
        x=500+(self.i%6)*1500;y=700+(self.i//6)*500;self.i+=1;return x,y
    def alias(self,a,b,w=1):
        x,y=self.pos();tunnel(self.c,x,y,a,w,'east');wire(self.c,(x,y),(x+80,y));tunnel(self.c,x+80,y,b,w)
    def const(self,v,w=1):
        s=self.fresh('constant');x,y=self.pos();constant(self.c,x,y,v,w);wire(self.c,(x,y),(x+40,y));tunnel(self.c,x+40,y,s,w);return s
    def gate(self,kind,a,b=None,w=1,out=None):
        s=out or self.fresh(kind.lower());x,y=self.pos()
        if kind=='NOT':
            component(self.c,1,'NOT Gate',x,y,size=20,width=w);port(self.c,x-20,y,a,w)
        else:
            component(self.c,1,kind+' Gate',x,y,size=30,inputs=2,width=w)
            axis=40 if kind in ('XOR','XNOR','NAND','NOR') else 30
            port(self.c,x-axis,y-10,a,w);port(self.c,x-axis,y+10,b,w)
        port(self.c,x,y,s,w,'right');return s
    def inv(self,a,w=1):return self.gate('NOT',a,w=w)
    def and_(self,*terms):
        a=terms[0]
        for b in terms[1:]:a=self.gate('AND',a,b)
        return a
    def or_(self,*terms):
        a=terms[0]
        for b in terms[1:]:a=self.gate('OR',a,b)
        return a
    def bits(self,a,w):
        x,y=self.pos(max(190,w*30));component(self.c,0,'Splitter',x,y,incoming=w,fanout=w,appear='right',facing='east',spacing=1)
        tunnel(self.c,x,y,a,w,'east');out=[]
        for i in range(w):
            s=self.fresh('bit');wire(self.c,(x+20,y+10*(i+1)),(x+80,y+10*(i+1)));tunnel(self.c,x+80,y+10*(i+1),s);out.append(s)
        return out
    def join(self,bits,out=None):
        s=out or self.fresh('bus');x,y=self.pos(max(190,len(bits)*30))
        component(self.c,0,'Splitter',x,y,incoming=len(bits),fanout=len(bits),appear='right',facing='east',spacing=1)
        tunnel(self.c,x,y,s,len(bits),'east')
        for i,b in enumerate(bits):wire(self.c,(x+20,y+10*(i+1)),(x+80,y+10*(i+1)));tunnel(self.c,x+80,y+10*(i+1),b)
        return s
    def eq(self,a,value,w):
        bits=self.bits(a,w);return self.and_(*[b if value>>i&1 else self.inv(b) for i,b in enumerate(bits)])
    def sub(self,name,inputs,outputs):
        x,y=self.pos(max(190,30*max(len(inputs),len(outputs))+50));E.SubElement(self.c,'comp',name=name,loc=loc(x,y))
        for i,(s,w) in enumerate(inputs):port(self.c,x-240,y+i*30,s,w)
        for i,(s,w) in enumerate(outputs):port(self.c,x,y+i*30,s,w,'right')
    def mux(self,a,b,select,w,out=None):
        s=out or self.fresh('mux');self.sub(f'ConsoleMux{w}',[(a,w),(b,w),(select,1)],[(s,w)]);return s
    def add(self,a,b,w,out=None):
        s=out or self.fresh('sum');self.sub(f'ConsoleAdd{w}',[(a,w),(b,w)],[(s,w)]);return s
    def reg(self,d,en,clk,reset,w,out):self.sub(f'ConsoleRegister{w}',[(d,w),(en,1),(clk,1),(reset,1)],[(out,w)])

def leaves(p):
    for w in (1,3,5,6,7,8,11):
        b=Builder(p,f'ConsoleMux{w}',[('A',w),('B',w),('Select',1)],[('Y',w)])
        mask=b.join(['Select']*w) if w>1 else 'Select'
        b.gate('OR',b.gate('AND','A',b.inv(mask,w),w),b.gate('AND','B',mask,w),w,out='Y')
    for w in (3,5,6,8):
        b=Builder(p,f'ConsoleAdd{w}',[('A',w),('B',w)],[('Y',w)])
        aa=b.bits('A',w);bb=b.bits('B',w);carry=b.const(0);yy=[]
        for a,bb in zip(aa,bb):
            xor=b.gate('XOR',a,bb);yy.append(b.gate('XOR',xor,carry));carry=b.or_(b.and_(a,bb),b.and_(xor,carry))
        b.join(yy,'Y')
    for w in (1,3,5,6,7,8):
        b=Builder(p,f'ConsoleRegister{w}',[('Data',w),('Load',1),('Clock',1),('Reset',1)],[('Q',w)])
        selected=b.mux('Q','Data','Load',w);bits=b.bits(selected,w) if w>1 else [selected];out=[]
        for i,s in enumerate(bits):
            x,y=b.pos();q=b.fresh('q');dff(b.c,x,y,s,'Clock',q,'Reset',f'bit{i}');out.append(q)
        if w>1:b.join(out,'Q')
        else:b.alias(out[0],'Q')

# Original, deliberately simple 5x7 glyph drawings. Seven rows; low bit is left.
GLYPHS={
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'B':['11110','10001','10001','11110','10001','10001','11110'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'F':['11111','10000','10000','11110','10000','10000','10000'],
 'G':['01111','10000','10000','10111','10001','10001','01111'],
 'H':['10001','10001','10001','11111','10001','10001','10001'],
 'I':['11111','00100','00100','00100','00100','00100','11111'],
 'J':['00111','00010','00010','00010','10010','10010','01100'],
 'K':['10001','10010','10100','11000','10100','10010','10001'],
 'L':['10000','10000','10000','10000','10000','10000','11111'],
 'M':['10001','11011','10101','10101','10001','10001','10001'],
 'N':['10001','11001','11001','10101','10011','10011','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'P':['11110','10001','10001','11110','10000','10000','10000'],
 'Q':['01110','10001','10001','10001','10101','10010','01101'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'S':['01111','10000','10000','01110','00001','00001','11110'],
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'U':['10001','10001','10001','10001','10001','10001','01110'],
 'V':['10001','10001','10001','10001','10001','01010','00100'],
 'W':['10001','10001','10001','10101','10101','10101','01010'],
 'X':['10001','10001','01010','00100','01010','10001','10001'],
 'Y':['10001','10001','01010','00100','00100','00100','00100'],
 'Z':['11111','00001','00010','00100','01000','10000','11111'],
 '0':['01110','10001','10011','10101','11001','10001','01110'],
 '1':['00100','01100','00100','00100','00100','00100','01110'],
 '2':['01110','10001','00001','00010','00100','01000','11111'],
 '3':['11110','00001','00001','01110','00001','00001','11110'],
 '4':['00010','00110','01010','10010','11111','00010','00010'],
 '5':['11111','10000','10000','11110','00001','00001','11110'],
 '6':['01110','10000','10000','11110','10001','10001','01110'],
 '7':['11111','00001','00010','00100','01000','01000','01000'],
 '8':['01110','10001','10001','01110','10001','10001','01110'],
 '9':['01110','10001','10001','01111','00001','00001','01110'],
 '.':['00000','00000','00000','00000','00000','00110','00110'],
 ',':['00000','00000','00000','00000','00110','00110','00100'],
 ':':['00000','00110','00110','00000','00110','00110','00000'],
 ';':['00000','00110','00110','00000','00110','00110','00100'],
 '>':['10000','01000','00100','00010','00100','01000','10000'],
 '<':['00001','00010','00100','01000','00100','00010','00001'],
 '=':['00000','00000','11111','00000','11111','00000','00000'],
 '+':['00000','00100','00100','11111','00100','00100','00000'],
 '-':['00000','00000','00000','11111','00000','00000','00000'],
 '/':['00001','00001','00010','00100','01000','10000','10000'],
 '\\':['10000','10000','01000','00100','00010','00001','00001'],
 '?':['01110','10001','00001','00010','00100','00000','00100'],
 '!':['00100','00100','00100','00100','00100','00000','00100'],
 '#':['01010','11111','01010','01010','11111','01010','00000'],
 '$':['00100','01111','10100','01110','00101','11110','00100'],
 '%':['11001','11010','00010','00100','01000','01011','10011'],
 '&':['01100','10010','10100','01000','10101','10010','01101'],
 '*':['00000','10101','01110','11111','01110','10101','00000'],
 '(' :['00010','00100','01000','01000','01000','00100','00010'],
 ')' :['01000','00100','00010','00010','00010','00100','01000'],
 '[' :['01110','01000','01000','01000','01000','01000','01110'],
 ']' :['01110','00010','00010','00010','00010','00010','01110'],
 '{' :['00011','00100','00100','01000','00100','00100','00011'],
 '}' :['11000','00100','00100','00010','00100','00100','11000'],
 '"':['01010','01010','01010','00000','00000','00000','00000'],
 "'":['00100','00100','01000','00000','00000','00000','00000'],
 '`':['01000','00100','00010','00000','00000','00000','00000'],
 '_':['00000','00000','00000','00000','00000','00000','11111'],
 '^':['00100','01010','10001','00000','00000','00000','00000'],
 '|':['00100','00100','00100','00100','00100','00100','00100'],
 '~':['00000','00000','01001','10110','00000','00000','00000'],
 '@':['01110','10001','10111','10101','10111','10000','01110'],
}
def font():
    values=[0]*1024
    for char in range(32,127):
        rows=GLYPHS.get(chr(char).upper(),['00000']*7)
        for row,pixels in enumerate(rows):values[char*8+row]=sum((p=='1')<<(i+1) for i,p in enumerate(pixels))
    return values

def terminal():
    p=project('Apple1Console');p[0].text='GENERATED by tools/generate_terminal.py; edit the generator, not this file.';E.SubElement(p,'lib',name='10',desc='jar#../../build/bitwright-console.jar#org.bitwright.console.ConsoleLibrary')
    leaves(p)
    bus_inputs=[('Address',16),('DataIn',8),('Write',1),('Read',1),('SysClock',1),('Reset',1)]
    bus_outputs=[('DataOut',8),('Ready',1),('Busy',1),('CursorX',6),('CursorY',5),('Origin',5)]
    logic_inputs=bus_inputs+[('HostValid',1),('HostASCII',7)]
    logic_outputs=bus_outputs+[('HostAck',1),('PixelColumn',6),('PixelY',8),('PixelBits',8),('PixelDraw',1)]
    b=Builder(p,'ConsoleLogic',logic_inputs,logic_outputs)
    zero=b.const(0);one=b.const(1);zero5=b.const(0,5);zero6=b.const(0,6);zero8=b.const(0,8)
    resetn=b.inv('Reset');falling=b.inv('SysClock')
    kdata=b.eq('Address',0xd010,16);kstatus=b.eq('Address',0xd011,16);display=b.eq('Address',0xd012,16)
    consume=b.and_(kdata,'Read','Ready',resetn)
    load=b.and_(b.inv('Ready'),'HostValid',resetn)
    b.reg(b.or_(b.and_('Ready',b.inv(consume)),load),one,'SysClock','Reset',1,'Ready')
    b.reg('HostASCII',load,'SysClock','Reset',7,'KeyboardByte')
    b.alias(load,'HostAck')
    kb=b.bits('KeyboardByte',7);keybyte=b.join(kb+['Ready']);readybyte=b.join([zero]*7+['Ready']);busybyte=b.join([zero]*7+['Busy'])
    result=b.mux(zero8,keybyte,kdata,8);result=b.mux(result,readybyte,kstatus,8);b.mux(result,busybyte,display,8,'DataOut')
    db=b.bits('DataIn',8);char=b.join(db[:7]);cr=b.or_(b.eq(char,13,7),b.eq(char,10,7));ff=b.eq(char,12,7)
    # Accepted writes, cursor controls and all character memory reside in the circuit.
    accept=b.and_('Write',display,b.inv('Busy'),resetn)
    printable=b.and_(b.or_(db[5],db[6]),b.inv(b.eq(char,127,7)))
    writechar=b.and_(accept,printable)
    wrap=b.and_(writechar,b.eq('CursorX',39,6));newline=b.or_(b.and_(accept,cr),wrap)
    clear=b.and_(accept,ff)
    b.reg(clear,one,falling,'Reset',1,'ClearPulse')
    device_reset=b.or_('Reset','ClearPulse')
    backspace=b.and_(accept,b.eq(char,8,7),b.inv(b.eq('CursorX',0,6)))
    bottom=b.eq('CursorY',23,5);scroll=b.and_(newline,bottom)
    incrementX=b.add('CursorX',b.const(1,6),6);nextX=b.mux(incrementX,zero6,newline,6)
    nextX=b.mux(nextX,b.add('CursorX',b.const(63,6),6),backspace,6)
    b.reg(nextX,b.or_(writechar,newline,backspace),falling,device_reset,6,'CursorX')
    incrementY=b.add('CursorY',b.const(1,5),5)
    b.reg(incrementY,b.and_(newline,b.inv(bottom)),falling,device_reset,5,'CursorY')
    originInc=b.add('Origin',b.const(1,5),5);originNext=b.mux(originInc,zero5,b.eq('Origin',23,5),5)
    b.reg(originNext,scroll,falling,device_reset,5,'Origin')
    clearDone=b.eq('ClearColumn',39,6)
    b.reg(b.or_(scroll,b.and_('ScrollBusy',b.inv(clearDone))),one,falling,device_reset,1,'ScrollBusy')
    b.alias(b.or_('ScrollBusy','ClearPulse','RenderBusy'),'Busy')
    # An accepted character is rendered immediately in eight raw pixel-word writes.
    # This remains gate logic: the Java adapter never receives character codes.
    renderStart=b.and_(writechar,b.inv(scroll))
    renderLast=b.eq('RenderRow',7,3)
    b.reg(b.or_(renderStart,b.and_('RenderBusy',b.inv(renderLast))),one,falling,device_reset,1,'RenderBusy')
    b.reg(char,renderStart,falling,device_reset,7,'RenderCharacter')
    b.reg('CursorX',renderStart,falling,device_reset,6,'RenderColumn')
    b.reg('CursorY',renderStart,falling,device_reset,5,'RenderCellRow')
    renderNext=b.mux(b.add('RenderRow',b.const(1,3),3),b.const(0,3),renderLast,3)
    b.reg(renderNext,'RenderBusy',falling,device_reset,3,'RenderRow')
    clearInc=b.add('ClearColumn',b.const(1,6),6);clearNext=b.mux(clearInc,zero6,clearDone,6)
    b.reg(clearNext,'ScrollBusy',falling,device_reset,6,'ClearColumn')
    def physicalrow(row):
        r=b.bits(row,5);o=b.bits('Origin',5);total=b.add(b.join(r+[zero]),b.join(o+[zero]),6)
        t=b.bits(total,6);over=b.or_(t[5],b.and_(t[4],t[3]));adjust=b.add(total,b.const(40,6),6)
        chosen=b.mux(total,adjust,over,6);return b.bits(chosen,6)[:5]
    # Scan 40 packed 8-pixel words per line, then 192 pixel rows.
    lastX=b.eq('ScanColumn',39,6);lastY=b.eq('ScanY',191,8)
    b.reg(b.mux(b.add('ScanColumn',b.const(1,6),6),zero6,lastX,6),one,falling,'Reset',6,'ScanColumn')
    b.reg(b.mux(b.add('ScanY',b.const(1,8),8),zero8,lastY,8),lastX,falling,'Reset',8,'ScanY')
    sy=b.bits('ScanY',8);scanRow=b.join(sy[3:]);scanAddress=b.join(b.bits('ScanColumn',6)+physicalrow(scanRow))
    cursorAddress=b.join(b.bits('CursorX',6)+physicalrow('CursorY'))
    eraseAddress=b.join(b.bits('ClearColumn',6)+physicalrow('CursorY'))
    writeAddress=b.mux(cursorAddress,eraseAddress,'ScrollBusy',11)
    writeEnable=b.or_(writechar,'ScrollBusy');address=b.mux(scanAddress,writeAddress,writeEnable,11)
    inputchar=b.mux(char,b.const(32,7),'ScrollBusy',7)
    x,y=b.pos();component(b.c,4,'RAM',x,y,addrWidth=11,dataWidth=7,appearance='classic',label='TEXT_RAM',labelvisible=True,databus='bibus',enables='byte',asyncread=True,trigger='falling',clearpin=True)
    port(b.c,x,y+10,address,11);port(b.c,x,y+50,writeEnable);port(b.c,x,y+60,one);port(b.c,x,y+70,'SysClock');port(b.c,x,y+90,inputchar,7)
    wire(b.c,(x+40,y),(x+40,y-30),(x+80,y-30));tunnel(b.c,x+80,y-30,device_reset)
    port(b.c,x+240,y+90,'ReadCharacter',7,'right')
    pixelRow=b.mux(b.join(sy[:3]),'RenderRow','RenderBusy',3)
    pixelChar=b.mux('ReadCharacter','RenderCharacter','RenderBusy',7)
    fontaddr=b.join(b.bits(pixelRow,3)+b.bits(pixelChar,7));x,y=b.pos()
    rom=component(b.c,4,'ROM',x,y,addrWidth=10,dataWidth=8,appearance='classic',label='ORIGINAL_5x7_FONT',labelvisible=True)
    contents=E.SubElement(rom,'a',name='contents');contents.text='addr/data: 10 8\n'+' '.join(f'{v:02x}' for v in font())
    port(b.c,x,y+10,fontaddr,10);port(b.c,x+240,y+60,'PixelBits',8,'right')
    draw=b.and_(b.inv(writeEnable),resetn)
    b.alias(draw,'PixelDraw')
    b.mux('ScanColumn','RenderColumn','RenderBusy',6,'PixelColumn')
    renderY=b.join(b.bits('RenderRow',3)+b.bits('RenderCellRow',5))
    b.mux('ScanY',renderY,'RenderBusy',8,'PixelY')
    # A compact front panel is kept separate from the inspectable controller hierarchy.
    c=circuit(p,'Apple1Console');c.find("a[@name='appearance']").set('val','custom')
    a=E.SubElement(c,'appear')
    E.SubElement(a,'rect',x='0',y='0',width='400',height='300',fill='#ffffff',stroke='#222222',**{'stroke-width':'2'})
    for i,(label,w) in enumerate(bus_inputs):
        source(c,100,120+i*50,label,w)
        E.SubElement(a,'circ-port',x='0',y=str(20+i*40),dir='in',pin=f'100,{120+i*50}')
        E.SubElement(a,'text',x='10',y=str(24+i*40),fill='#222222',**{'font-family':'SansSerif','font-size':'12'}).text=label
    for i,(label,w) in enumerate(bus_outputs):
        sink(c,1150,120+i*50,label,w)
        yy=60+i*40;E.SubElement(a,'circ-port',x='400',y=str(yy),dir='out',pin=f'1150,{120+i*50}')
        E.SubElement(a,'text',x='390',y=str(yy+4),fill='#222222',**{'font-family':'SansSerif','font-size':'12','text-anchor':'end'}).text=label
    E.SubElement(a,'text',x='200',y='125',fill='#222222',**{'font-family':'SansSerif','font-size':'16','text-anchor':'middle'}).text='Apple-1-style console'
    E.SubElement(a,'text',x='200',y='145',fill='#222222',**{'font-family':'SansSerif','font-size':'11','text-anchor':'middle'}).text='Open: keyboard + pixel display'
    E.SubElement(a,'circ-anchor',x='400',y='140',facing='east')
    text(c,60,35,'BITWRIGHT / GATE-BUILT 40 x 24 TERMINAL')
    text(c,60,60,'Poke the screen to type. Load .mon files through the button. CPU firmware consumes the ASCII stream.')
    x,y=420,110;component(c,10,'ConsoleHost',x,y)
    for dy,label,w in [(20,'SysClock',1),(50,'Reset',1),(80,'HostAck',1),(110,'PixelDraw',1),(140,'PixelColumn',6),(170,'PixelY',8),(200,'PixelBits',8)]:port(c,x,y+dy,label,w)
    for dy,label,w in [(30,'HostValid',1),(60,'HostASCII',7),(90,'HostOverflow',1)]:port(c,x+380,y+dy,label,w,'right')
    text(c,420,435,'HOST ADAPTER: ASCII capture and raw retained pixels only.')
    text(c,60,475,'Open ConsoleLogic below to inspect MMIO, keyboard latch, cursor, wrapping, scrolling, RAM scan and font lookup.')
    x,y=650,550;E.SubElement(c,'comp',name='ConsoleLogic',loc=loc(x,y))
    for i,(label,w) in enumerate(logic_inputs):port(c,x-240,y+i*30,label,w)
    for i,(label,w) in enumerate(logic_outputs):port(c,x,y+i*30,label,w,'right')
    sink(c,1150,440,'HostOverflow')
    text(c,60,945,'Display: original 5x7 glyphs in 8x8 cells; digital scan. No NTSC or cycle-exact Apple-1 claim.')
    return p

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');args=ap.parse_args()
    path=ROOT/'circuits/generated/terminal.circ';data=serialize(terminal())
    if args.check:
        if not path.exists() or path.read_text()!=data:ap.exit(1,'Stale generated terminal.circ\n')
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
    print('Gate-built terminal artifact is current.' if args.check else 'Generated gate-built terminal.circ.')
if __name__=='__main__':main()
