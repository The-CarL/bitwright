import com.cburch.logisim.circuit.Analyze;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.circuit.SubcircuitFactory;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.memory.Mem;
import com.cburch.logisim.std.wiring.Pin;
import org.bitwright.console.ConsoleHost;
import org.bitwright.console.ConsoleState;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** End-to-end test of the delivered native machine; Java supplies ASCII, never instructions/RAM. */
public final class MachineSmoke {
  final CircuitState state, console;
  final Component host, ram;
  final Map<String,Instance> inputs=new HashMap<>(), outputs=new HashMap<>(), consoleOutputs=new HashMap<>();
  final StringBuilder transcript=new StringBuilder();
  int cycles, checks, writes;
  final List<String> metrics=new ArrayList<>();
  final long started=System.nanoTime();
  MachineSmoke(CircuitState s) {
    state=s;
    for(var e:Analyze.getPinLabels(s.getCircuit()).entrySet())
      (Pin.FACTORY.isInputPin(e.getKey())?inputs:outputs).put(e.getValue(),e.getKey());
    var comp=component(s,"Apple1Console");
    console=((SubcircuitFactory)comp.getFactory()).getSubstate(s,comp);
    host=component(console,"ConsoleHost");ram=component(s,"RAM");
    for(var e:Analyze.getPinLabels(console.getCircuit()).entrySet())if(!Pin.FACTORY.isInputPin(e.getKey()))consoleOutputs.put(e.getValue(),e.getKey());
    state.getPropagator().propagate();
  }
  static Component component(CircuitState s,String name) {
    return s.getCircuit().getNonWires().stream().filter(c->c.getFactory().getName().equals(name)).findFirst().orElseThrow();
  }
  void input(String name,int value) {
    var p=inputs.get(name);Pin.FACTORY.driveInputPin(state.getInstanceState(p),Value.createKnown(Pin.FACTORY.getWidth(p),value));
    state.markComponentAsDirty(p.getComponent());settle();
  }
  void settle(){state.getPropagator().propagate();if(state.getPropagator().isOscillating())throw new AssertionError("Machine oscillation");}
  int out(String name){var v=Pin.FACTORY.getValue(state.getInstanceState(outputs.get(name)));if(!v.isFullyDefined())throw new AssertionError(name+" undefined: "+v);return (int)v.toLongValue();}
  int consoleOut(String name){var v=Pin.FACTORY.getValue(console.getInstanceState(consoleOutputs.get(name)));if(!v.isFullyDefined())throw new AssertionError("Console "+name+" undefined: "+v);return (int)v.toLongValue();}
  ConsoleState host(){return ConsoleHost.data(console.getInstanceState(Instance.getInstanceFor(host)));}
  long memory(int address){return ((Mem)ram.getFactory()).getContents(state.getInstanceState(Instance.getInstanceFor(ram))).get(address);}
  void cycle(){
    state.getPropagator().toggleClocks();settle();
    if(out("Fault")!=0)throw new AssertionError("CPU fault PC="+Integer.toHexString(out("PC"))+" IR="+Integer.toHexString(out("IR")));
    if(out("Write")!=0){writes++;if(out("Address")==0xd012){
      if(consoleOut("Busy")!=0)throw new AssertionError("CPU attempted display write while busy at PC="+Integer.toHexString(out("PC")));
      transcript.append((char)(out("WriteData")&127));
    }}
    state.getPropagator().toggleClocks();settle();cycles++;
    if(cycles%5000==0)System.out.printf(Locale.ROOT,"Progress: cycles=%d seconds=%.1f PC=%04X queued=%d tail=%s%n",cycles,(System.nanoTime()-started)/1e9,out("PC"),host().queued(),transcript.substring(Math.max(0,transcript.length()-100)).replace("\r","\\r"));
  }
  void expect(boolean ok,String why){checks++;if(!ok)throw new AssertionError(why+" PC="+Integer.toHexString(out("PC"))+"\n"+transcript);}
  void until(String suffix,int budget){
    int end=cycles+budget;
    while(!transcript.toString().endsWith(suffix)&&cycles<end)cycle();
    expect(transcript.toString().endsWith(suffix),"watchdog waiting for "+suffix);
  }
  void capture(String text){for(char c:text.toCharArray())if(!host().capture(c))throw new AssertionError("ASCII rejected");console.markComponentAsDirty(host);settle();}
  void load(Path records){try{host().load(records);}catch(Exception e){throw new IllegalStateException(e);}console.markComponentAsDirty(host);settle();}
  void reset(){input("Reset",1);input("Reset",0);}
  static boolean glyphMatches(ConsoleState image,int column,int row,char character) {
    // Independent expected 8x8 bitmaps: bit0 left; the visible glyph occupies columns1..5.
    int[] bitmap=switch(character){
      case 'K' -> new int[]{0x22,0x12,0x0A,0x06,0x0A,0x12,0x22,0};
      case '9' -> new int[]{0x1C,0x22,0x22,0x3C,0x20,0x20,0x1C,0};
      default -> throw new IllegalArgumentException("No independent expected glyph for "+character);
    };
    for(int y=0;y<8;y++)for(int x=0;x<8;x++)
      if(image.pixel(column*8+x,row*8+y)!=((bitmap[y]&(1<<x))!=0))return false;
    return true;
  }
  void program(Path root,String name,String prompt,String input,String result) throws Exception {
    transcript.setLength(0);
    int loadCycle=cycles;long loadStart=System.nanoTime();
    load(root.resolve("images/memory/6502-"+name+".mon"));
    // Committed demo records end in 0300R: the firmware loads and starts them.
    until(prompt,300000);
    double loadSeconds=(System.nanoTime()-loadStart)/1e9;
    metrics.add(String.format(Locale.ROOT,"{\"kind\":\"file_to_program_prompt\",\"program\":\"%s\",\"cycles\":%d,\"seconds\":%.6f}",name,cycles-loadCycle,loadSeconds));
    System.out.printf(Locale.ROOT,"Metric: %s file to program input prompt: %d cycles, %.3f seconds.%n",name,cycles-loadCycle,loadSeconds);
    expect(host().queued()==0,name+" load records consumed by firmware");
    byte[] expected=Files.readAllBytes(root.resolve("images/memory/6502-"+name+".bin"));
    for(int i=0;i<expected.length;i++)expect(memory(0x300+i)==(expected[i]&255),name+" loaded RAM byte "+i);
    if(!input.isEmpty()){
      int echoStart=transcript.length(),keyCycle=cycles,echoX=consoleOut("CursorX"),echoY=consoleOut("CursorY");
      long keyStart=System.nanoTime();capture(input);
      int end=cycles+20000;
      while(transcript.length()==echoStart&&cycles<end)cycle();
      expect(transcript.substring(echoStart).equals(input),name+" echoes actual keyboard input first");
      for(int i=0;i<8;i++)cycle(); // Circuit renderer completes this glyph in eight cycles.
      double keySeconds=(System.nanoTime()-keyStart)/1e9;
      expect(glyphMatches(host(),echoX,echoY,input.charAt(0)),name+" actual 8x8 echo glyph matches at captured cursor");
      metrics.add(String.format(Locale.ROOT,"{\"kind\":\"input_to_echo_pixels\",\"program\":\"%s\",\"input\":\"%s\",\"cycles\":%d,\"seconds\":%.6f}",name,input,cycles-keyCycle,keySeconds));
      System.out.printf(Locale.ROOT,"Metric: %s input '%s' to circuit echo pixels: %d cycles, %.3f seconds (headless; GUI scheduling excluded).%n",name,input,cycles-keyCycle,keySeconds);
    }
    if(!result.isEmpty())until(result,100000);
    until("\\ ",100000);
    expect(host().queued()==0,name+" consumes input");
    System.out.println("Native machine: loaded and executed "+name+"; "+cycles+" cycles, transcript="+transcript.toString().replace("\r","\\r"));
  }
  void test(Path root,boolean bootOnly)throws Exception{
    reset();until("\\ ",20000);
    expect(transcript.toString().contains("BITWRIGHT"),"firmware banner");
    System.out.println("Native machine: firmware booted on circuit CPU, "+cycles+" cycles.");
    if(bootOnly)return;
    Files.deleteIfExists(root.resolve("build/test-results/machine-native.json"));
    program(root,"hello","PRESS A KEY: ","K","K\r");
    program(root,"sum","DIGIT 0-9: ","9","SUM (HEX) = 2D\r");
    expect(memory(0x80)==45,"sum computed in real RAM");
    int saved=(int)memory(0x300);transcript.setLength(0);reset();until("\\ ",20000);
    expect(transcript.toString().contains("BITWRIGHT 6502"),"warm reset executes firmware and prints a new banner");
    expect(memory(0x300)==saved,"warm reset preserves RAM");
    // The circuit dirty-character renderer supplies visible pixels within eight cycles.
    // Full-frame/scroll correctness is covered independently by TerminalSmoke.
    for(int i=0;i<8;i++)cycle();
    boolean lit=false;for(int y=0;y<192&&!lit;y++)for(int x=0;x<320;x++)if(host().pixel(x,y)){lit=true;break;}
    expect(lit,"native terminal scan supplies visible pixels");
    double seconds=(System.nanoTime()-started)/1e9;
    System.out.printf(Locale.ROOT,"Native machine: %d assertions passed; %d cycles; %d writes; %.3f seconds; %.1f cycles/s.%n",checks,cycles,writes,seconds,cycles/seconds);
    Path report=root.resolve("build/test-results/machine-native.json");Files.createDirectories(report.getParent());
    String json=String.format(Locale.ROOT,"{\n  \"status\":\"pass\",\n  \"assertions\":%d,\n  \"cycles\":%d,\n  \"writes\":%d,\n  \"seconds\":%.6f,\n  \"cycles_per_second\":%.6f,\n  \"host_writes_program_ram\":false,\n  \"gui_verified\":false,\n  \"metrics\":[%s]\n}\n",checks,cycles,writes,seconds,cycles/seconds,String.join(",",metrics));
    Files.writeString(report,json);
    System.out.println("Native machine report: "+report);
  }
  public static void main(String[] args){
    try{var f=new Loader(null).openLogisimFile(new File(args[0]));var p=new Project(f);
      try{new MachineSmoke(CircuitState.createRootState(p,f.getMainCircuit(),Thread.currentThread())).test(Path.of(args[1]),args.length>2&&args[2].equals("--boot-only"));}
      finally{p.getSimulator().shutDown();}System.exit(0);
    }catch(Exception|AssertionError e){e.printStackTrace();System.exit(1);}
  }
}
