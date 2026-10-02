import com.cburch.logisim.circuit.Analyze;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Exercises the actual gate circuit. RAM is an external bus test fixture. */
public final class Cpu6502Smoke {
  final CircuitState state;
  final Map<String,Instance> inputs=new HashMap<>(),outputs=new HashMap<>();
  final byte[] memory=new byte[65536];
  int cycles,checks,writes;
  final List<String> instructionWrites=new ArrayList<>();
  Cpu6502Smoke(CircuitState s) {
    state=s;
    for(var e:Analyze.getPinLabels(s.getCircuit()).entrySet())
      (Pin.FACTORY.isInputPin(e.getKey())?inputs:outputs).put(e.getValue(),e.getKey());
  }
  void input(String name,int value) {
    var pin=inputs.get(name);
    Pin.FACTORY.driveInputPin(state.getInstanceState(pin),Value.createKnown(Pin.FACTORY.getWidth(pin),value));
    state.markComponentAsDirty(pin.getComponent());
    state.getPropagator().propagate();
    if(state.getPropagator().isOscillating())throw new AssertionError("oscillation");
  }
  int output(String name) {
    var v=Pin.FACTORY.getValue(state.getInstanceState(outputs.get(name)));
    if(!v.isFullyDefined())throw new AssertionError("undefined "+name+"="+v);
    return (int)v.toLongValue();
  }
  void cycle() {
    input("SysClock",0);
    if(output("Write")!=0){memory[output("Address")]=(byte)output("DataOut");writes++;instructionWrites.add(output("Address")+":"+output("DataOut"));}
    input("DataIn",Byte.toUnsignedInt(memory[output("Address")]));
    input("SysClock",1);cycles++;
  }
  void reset(int pc) {
    memory[0xfffc]=(byte)pc;memory[0xfffd]=(byte)(pc>>8);
    input("IRQ",0);input("NMI",0);input("SysClock",0);input("DataIn",0);input("Reset",1);input("Reset",0);
    cycle();cycle();
    expect(output("PC")==pc && output("Sync")==1,"reset vector PC="+Integer.toHexString(output("PC")));
  }
  void expect(boolean yes,String what){checks++;if(!yes)throw new AssertionError(what+" state="+output("State")+" pc="+Integer.toHexString(output("PC"))+" ir="+Integer.toHexString(output("IR")));}
  void program(int start,int...bytes){for(int i=0;i<bytes.length;i++)memory[start+i]=(byte)bytes[i];}
  void until(int pc,int bound){for(int i=0;i<bound;i++){if(output("Sync")==1&&output("PC")==pc)return;if(output("Fault")!=0)throw new AssertionError("CPU fault PC="+Integer.toHexString(output("PC")));cycle();}throw new AssertionError("watchdog PC="+Integer.toHexString(output("PC"))+" state="+output("State"));}
  void test(){
    // Sum 1..5 using a loop, zero-page memory, JSR/RTS and stack preservation.
    program(0x200,0xa2,5,0xa9,0,0x85,0x20,0x8a,0x18,0x65,0x20,0x85,0x20,0xca,0xd0,0xf7,0x20,0x30,2,0x8d,0x12,0xd0,0xea);
    program(0x230,0x48,0xa9,0x55,0x68,0x60);
    reset(0x200);until(0x215,300);
    expect(output("A")==15,"loop arithmetic A=15");expect(Byte.toUnsignedInt(memory[0x20])==15,"RAM sum=15");expect(Byte.toUnsignedInt(memory[0xd012])==15,"MMIO write=15");expect(output("SP")==0xfd,"stack restored");
    // Indexed address crossing, zero-page indirect wrapping and signed branch.
    program(0x300,0xa2,1,0xa0,2,0xa9,0x42,0x9d,0xff,3,0xb1,0xff,0x49,0xff,0x8d,1,4,0xea);
    memory[0xff]=(byte)0xfe;memory[0]=3;
    reset(0x300);until(0x311,160);
    expect(Byte.toUnsignedInt(memory[0x400])==0x42,"absolute X page carry");expect(Byte.toUnsignedInt(memory[0x401])==0xbd,"indirect Y zero-page wrap");
    // Binary overflow, carry/no-borrow and accumulator shift flags.
    program(0x500,0xa9,0x7f,0x18,0x69,1,0x08,0x68,0x85,0x30,0xa9,0,0x38,0xe9,1,0x85,0x31,0x6a,0xea);
    reset(0x500);until(0x512,140);
    expect((memory[0x30]&0xc3)==0xc0,"ADC signed overflow/N flags");expect(Byte.toUnsignedInt(memory[0x31])==255,"SBC borrow");expect(output("A")==0x7f&&(output("P")&1)==1,"ROR carry");
    // Decimal NMOS behavior: ADC carry plus binary Z, SBC borrow adjustment.
    program(0x700,0xf8,0xa9,0x45,0x18,0x69,0x55,0x08,0x68,0x85,0x32,0xa9,0,0x38,0xe9,1,0xd8,0xea);
    reset(0x700);until(0x710,140);
    expect((memory[0x32]&0xc3)==0xc1,"decimal ADC flags use pre-adjust intermediates");
    expect(output("A")==0x99&&(output("P")&1)==0,"decimal SBC 00-01=99 borrow");
    // BRK/RTI and hardware IRQ/NMI use different stacked B bits and vectors.
    program(0x800,0x58,0xea,0xea,0x00,0xea,0xea);
    program(0x900,0xe6,0x40,0x40);program(0x920,0xe6,0x41,0x40);
    memory[0xfffe]=0;memory[0xffff]=9;memory[0xfffa]=0x20;memory[0xfffb]=9;
    reset(0x800);until(0x801,40);input("IRQ",1);cycle();input("IRQ",0);until(0x900,30);
    expect((memory[0x1fb]&0x10)==0,"hardware IRQ pushes B clear");until(0x801,60);
    expect(memory[0x40]==1&&output("SP")==0xfd,"IRQ RTI restores PC/SP");
    input("NMI",1);cycle();until(0x920,30);until(0x801,60);
    expect(memory[0x41]==1,"NMI vector and return");cycle();until(0x802,30);
    expect(memory[0x41]==1,"held NMI does not retrigger");input("NMI",0);
    until(0x900,60);expect((memory[0x1fb]&0x10)!=0,"BRK pushes B set");until(0x805,60);
    expect(memory[0x40]==2&&output("SP")==0xfd,"BRK skips padding and RTI restores stack");
    // A one-clock NMI pulse inside an instruction is retained until its boundary.
    program(0xa00,0xea,0xea);reset(0xa00);cycle();input("NMI",1);cycle();input("NMI",0);cycle();until(0x920,40);until(0xa01,60);
    expect(memory[0x41]==2,"NMI pulse is retained across instruction execution");
    // Illegal instruction is a visible fault with no write.
    program(0x600,2);reset(0x600);cycle();cycle();expect(output("Fault")==1&&output("Write")==0,"illegal opcode fault");
    input("Reset",1);expect(output("Write")==0&&output("Read")==0,"reset suppresses transactions");input("Reset",0);
    System.out.println("Native gate CPU: "+checks+" checks passed, "+cycles+" microcycles, "+writes+" writes.");
  }
  void cases(String path) throws Exception {
    for(String line:Files.readAllLines(Path.of(path))) {
      if(line.isBlank()||line.startsWith("#"))continue;
      String[] fields=line.split("\\t");
      Arrays.fill(memory,(byte)0);
      for(String patch:fields[3].split(";")) {
        String[] parts=patch.split("=");int address=Integer.parseInt(parts[0],16);
        byte[] data=HexFormat.of().parseHex(parts[1]);
        for(int j=0;j<data.length;j++)memory[(address+j)&65535]=data[j];
      }
      reset(Integer.parseInt(fields[1],16));
      System.out.println("CASE\t"+fields[0]);
      for(int instruction=0;instruction<Integer.parseInt(fields[2]);instruction++) {
        instructionWrites.clear();int bound=50;
        do {cycle();if(output("Fault")!=0)throw new AssertionError("Fault in "+fields[0]+" PC="+output("PC"));if(--bound==0)throw new AssertionError("Instruction watchdog "+fields[0]);}while(output("Sync")==0);
        System.out.println("STATE\t"+output("PC")+"\t"+output("A")+"\t"+output("X")+"\t"+output("Y")+"\t"+output("SP")+"\t"+output("P")+"\t"+String.join(",",instructionWrites));
      }
    }
  }
  static void foundations(Project p,com.cburch.logisim.file.LogisimFile f) {
    var adder=new Cpu6502Smoke(CircuitState.createRootState(p,f.getCircuit("FullAdder"),Thread.currentThread()));
    for(int v=0;v<8;v++) {
      adder.input("A",v&1);adder.input("B",(v>>1)&1);adder.input("CarryIn",(v>>2)&1);
      int sum=Integer.bitCount(v);
      if(adder.output("Sum")!=(sum&1)||adder.output("CarryOut")!=(sum>>1))throw new AssertionError("FullAdder truth table "+v);
    }
    var cell=new Cpu6502Smoke(CircuitState.createRootState(p,f.getCircuit("GateDff"),Thread.currentThread()));
    cell.input("SysClock",0);cell.input("Data",0);cell.input("Reset",1);cell.input("Reset",0);
    for(int i=0;i<16;i++) {
      int value=i%2;cell.input("Data",value);cell.input("SysClock",1);
      if(cell.output("Q")!=value)throw new AssertionError("gate DFF rising capture");
      cell.input("Data",1-value);if(cell.output("Q")!=value)throw new AssertionError("gate DFF high hold");
      cell.input("SysClock",0);if(cell.output("Q")!=value)throw new AssertionError("gate DFF falling hold");
    }
    cell.input("Reset",1);if(cell.output("Q")!=0)throw new AssertionError("gate DFF asynchronous reset");
    var bank=new Cpu6502Smoke(CircuitState.createRootState(p,f.getCircuit("Register8R0"),Thread.currentThread()));
    bank.input("SysClock",0);bank.input("Enable",0);bank.input("Data",0xaa);bank.input("Reset",1);bank.input("Reset",0);bank.input("SysClock",1);
    if(bank.output("Q")!=0)throw new AssertionError("disabled bank holds after rising edge");
    bank.input("Enable",1);bank.input("Data",0x55);
    if(bank.output("Q")!=0)throw new AssertionError("enable rising during high clock cannot capture");
    bank.input("SysClock",0);bank.input("SysClock",1);
    if(bank.output("Q")!=0x55)throw new AssertionError("enabled bank captures on next clock edge");
    bank.input("Enable",0);bank.input("Data",0xaa);
    if(bank.output("Q")!=0x55)throw new AssertionError("disable during high clock preserves capture");
    bank.input("SysClock",0);bank.input("SysClock",1);
    if(bank.output("Q")!=0x55)throw new AssertionError("disabled bank does not capture new data");
    bank.input("Enable",1);bank.input("Reset",1);
    if(bank.output("Q")!=0)throw new AssertionError("bank reset overrides clock enable");
    bank.input("Reset",0);
    if(bank.output("Q")!=0)throw new AssertionError("reset release during high clock cannot capture");
    bank.input("SysClock",0);bank.input("SysClock",1);
    if(bank.output("Q")!=0xaa)throw new AssertionError("bank resumes after reset on next rising edge");
    System.out.println("Native foundations: 8 FullAdder truth rows and 49 gate-DFF capture/hold/reset checks and 8 bank clock-enable checks passed.");
  }
  public static void main(String[] args) {
    try {
      if(args.length!=1 && args.length!=3)throw new IllegalArgumentException("Usage: Cpu6502Smoke circuit.circ [--cases cases.tsv | --roundtrip saved.circ]");
      var loader=new Loader(null);
      var file=loader.openLogisimFile(new File(args[0]));
      if(args.length==3 && args[1].equals("--roundtrip")) {
        var destination=new File(args[2]);
        if(!loader.save(file,destination))throw new AssertionError("Native save failed");
        file=new Loader(null).openLogisimFile(destination);
      }
      var project=new Project(file);
      try {
        var test=new Cpu6502Smoke(CircuitState.createRootState(project,file.getCircuit("Cpu6502"),Thread.currentThread()));
        if(args.length==3 && args[1].equals("--cases"))test.cases(args[2]);
        else {foundations(project,file);test.test();}
      } finally {project.getSimulator().shutDown();}
      System.exit(0);
    } catch(Exception|AssertionError failure) {failure.printStackTrace();System.exit(1);}
  }
}
