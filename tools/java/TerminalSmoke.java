import com.cburch.logisim.circuit.Analyze;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;
import org.bitwright.console.ConsoleHost;
import org.bitwright.console.ConsoleState;
import java.io.File;
import java.util.HashMap;
import java.util.Map;

/** Drives the actual native terminal logic. No terminal behavior is simulated in Java. */
public final class TerminalSmoke {
  private final CircuitState state;
  private final Map<String,Instance> inputs=new HashMap<>(),outputs=new HashMap<>();
  private final Component host;
  private int checks;
  TerminalSmoke(CircuitState state){
    this.state=state;
    for(var e:Analyze.getPinLabels(state.getCircuit()).entrySet())(Pin.FACTORY.isInputPin(e.getKey())?inputs:outputs).put(e.getValue(),e.getKey());
    host=state.getCircuit().getNonWires().stream().filter(c->c.getFactory().getName().equals("ConsoleHost")).findFirst().orElseThrow();
    state.getPropagator().propagate();
  }
  void input(String name,int value){
    var p=inputs.get(name);if(p==null)throw new AssertionError("Missing pin "+name);
    Pin.FACTORY.driveInputPin(state.getInstanceState(p),Value.createKnown(Pin.FACTORY.getWidth(p),value));
    state.markComponentAsDirty(p.getComponent());state.getPropagator().propagate();
    if(state.getPropagator().isOscillating())throw new AssertionError("Oscillating after "+name);
  }
  long output(String name){var p=outputs.get(name);var v=Pin.FACTORY.getValue(state.getInstanceState(p));if(!v.isFullyDefined())throw new AssertionError(name+" undefined: "+v);return v.toLongValue();}
  ConsoleState host(){return ConsoleHost.data(state.getInstanceState(Instance.getInstanceFor(host)));}
  void capture(String text){for(char c:text.toCharArray())host().capture(c);state.markComponentAsDirty(host);state.getPropagator().propagate();}
  void cycle(){input("SysClock",1);input("SysClock",0);}
  void expect(boolean value,String why){checks++;if(!value)throw new AssertionError(why);}
  void write(int value){int watchdog=100;while(output("Busy")!=0&&watchdog-->0)cycle();expect(watchdog>0,"display busy bounded");input("Address",0xd012);input("DataIn",value);input("Write",1);cycle();input("Write",0);}
  void test()throws Exception{
    for(var name:inputs.keySet())input(name,0);
    input("Reset",1);input("Reset",0);
    expect(output("Ready")==0&&output("Busy")==0&&output("CursorX")==0&&output("CursorY")==0,"reset clears circuit state");
    capture("AB");cycle();expect(output("Ready")==1&&host().queued()==1,"circuit latches and host acknowledges exactly one byte");
    input("Address",0xd011);expect(output("DataOut")==128,"keyboard ready status");
    input("Address",0xd010);expect(output("DataOut")==193,"keyboard data contains high-bit marker");
    cycle();expect(output("DataOut")==193&&host().queued()==1,"no read transaction leaves byte stable");
    input("Read",1);input("SysClock",1);expect(output("Ready")==0,"read acknowledges after rising capture");input("SysClock",0);input("Read",0);
    cycle();expect(output("DataOut")==194&&host().queued()==0,"next byte delivered separately");
    input("Read",1);cycle();input("Read",0);input("Address",0);
    expect(output("Ready")==0&&output("DataOut")==0,"empty input and unmapped read");
    write('A');expect(output("CursorX")==1&&output("CursorY")==0,"character advances circuit cursor");
    expect(output("Busy")==1,"accepted character reports busy during circuit pixel rendering");
    for(int i=0;i<8;i++)cycle();
    expect(output("Busy")==0,"dirty character rendering finishes after eight pixel-word cycles");
    expect(host().pixel(2,0)&&host().pixel(3,0)&&host().pixel(4,0)&&!host().pixel(1,0),"circuit RAM scan and font ROM render A top row");
    expect(host().pixel(1,3)&&host().pixel(5,3),"A crossbar pixel bitmap");
    for(int i=1;i<40;i++)write('B');expect(output("CursorX")==0&&output("CursorY")==1,"40th character wraps to next line");
    write(13);expect(output("CursorX")==0&&output("CursorY")==2,"CR advances one row");
    for(int i=2;i<24;i++)write(13);
    expect(output("Origin")==1&&output("CursorY")==23&&output("Busy")==1,"bottom newline starts circular scrolling and clear");
    for(int i=0;i<40;i++)cycle();expect(output("Busy")==0,"scroll clears exactly 40 columns and returns ready");
    write('Z');for(int i=0;i<8000;i++)cycle();
    expect(host().pixel(1,184)&&host().pixel(5,184),"bottom row renders after circuit scrolling");
    expect(!host().pixel(2,0),"old first line scrolled away");
    for(int i=0;i<23;i++)write(13);
    for(int i=0;i<40;i++)cycle();expect(output("Origin")==0&&output("CursorY")==23,"circular row origin wraps modulo 24");
    write('Z');
    write(8);expect(output("CursorX")==0,"backspace moves left without crossing row boundary");
    write(8);expect(output("CursorX")==0,"backspace at column zero stays in bounds");
    write('A');for(int i=0;i<8;i++)cycle();
    input("Address",0xd012);input("DataIn",12);input("Write",1);
    expect(output("CursorX")==1,"form feed does not commit before clock edge");
    cycle();input("Write",0);expect(output("CursorX")==0&&output("CursorY")==0&&output("Busy")==1,"form feed clears cursor on falling edge and holds busy");
    cycle();expect(output("Busy")==0,"clear pulse completes in one cycle");
    write('A');for(int i=0;i<8000;i++)cycle();expect(host().pixel(2,0)&&!host().pixel(1,184),"first character after form feed is retained and old screen clears");
    input("Reset",1);input("Reset",0);for(int i=0;i<8000;i++)cycle();
    expect(!host().pixel(1,184)&&output("CursorX")==0&&output("Origin")==0,"reset clears character RAM and cursor");
    System.out.println("Native terminal: "+checks+" assertions passed (MMIO keyboard latch, exact ack, font scan, wrap, scroll, reset).");
  }
  public static void main(String[] args){
    try{var file=new Loader(null).openLogisimFile(new File(args[0]));var project=new Project(file);
      try{new TerminalSmoke(CircuitState.createRootState(project,file.getMainCircuit(),Thread.currentThread())).test();}finally{project.getSimulator().shutDown();}System.exit(0);
    }catch(Exception|AssertionError failure){failure.printStackTrace();System.exit(1);}
  }
}
