import com.cburch.logisim.circuit.Analyze;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.io.Keyboard;
import com.cburch.logisim.std.wiring.Pin;
import java.io.File;
import java.util.HashMap;
import java.util.Map;

/** Native Keyboard/TTY circuit tests; pinned state inspection, never desktop interaction. */
public final class M0TextSmoke {
  private final CircuitState state;
  private final Map<String, Instance> inputs = new HashMap<>();
  private final Map<String, Instance> outputs = new HashMap<>();
  private final Component keyboard;
  private final Component tty;
  private int checks;

  private M0TextSmoke(CircuitState state) {
    this.state = state;
    for (var entry : Analyze.getPinLabels(state.getCircuit()).entrySet()) {
      (Pin.FACTORY.isInputPin(entry.getKey()) ? inputs : outputs).put(entry.getValue(), entry.getKey());
    }
    keyboard = component("Keyboard");
    tty = component("TTY");
    state.getPropagator().propagate();
  }

  private Component component(String name) {
    var matches = state.getCircuit().getNonWires().stream()
        .filter(c -> c.getFactory().getName().equals(name)).toList();
    if (matches.size() != 1) throw new IllegalStateException("Expected exactly one " + name);
    return matches.getFirst();
  }

  private void input(String name, int value) {
    var pin = inputs.get(name);
    if (pin == null) throw new IllegalStateException("Missing input " + name);
    Pin.FACTORY.driveInputPin(state.getInstanceState(pin), Value.createKnown(Pin.FACTORY.getWidth(pin), value));
    state.markComponentAsDirty(pin.getComponent());
    state.getPropagator().propagate();
  }

  private long output(String name) {
    var pin = outputs.get(name);
    if (pin == null) throw new IllegalStateException("Missing output " + name);
    var value = Pin.FACTORY.getValue(state.getInstanceState(pin));
    if (!value.isFullyDefined()) throw new AssertionError("Unknown output " + name + ": " + value);
    return value.toLongValue();
  }

  private void enqueue(String text) {
    Keyboard.addToBuffer(state.getInstanceState(Instance.getInstanceFor(keyboard)), text.toCharArray());
    state.markComponentAsDirty(keyboard);
    state.getPropagator().propagate();
  }

  private void cycle() {
    for (int i = 0; i < 2; i++) {
      state.getPropagator().toggleClocks();
      state.getPropagator().propagate();
      if (state.getPropagator().isOscillating()) throw new AssertionError("Oscillation during text test");
    }
  }

  private String row(int index) throws Exception {
    // TtyState is package-private in 5.0.0. Inspect its public row accessor on
    // the actual simulator instance instead of reimplementing text rendering.
    var data = state.getData(tty);
    var method = data.getClass().getDeclaredMethod("getRowString", int.class);
    method.setAccessible(true);
    return (String) method.invoke(data, index);
  }

  private void expect(boolean condition, String context) {
    checks++;
    if (!condition) throw new AssertionError(context);
  }

  private void reset() {
    input("Reset", 1);
    input("Reset", 0);
  }

  private void test() throws Exception {
    input("Run", 0); input("Clear", 0); reset();
    expect(row(0).isEmpty() && output("Available") == 0, "reset starts empty");
    enqueue("AB");
    expect(output("Available") == 1 && output("ASCII") == 65, "queue exposes first ASCII byte");
    expect(output("Transfer") == 0, "Run=0 disables transfer");
    for (int i = 0; i < 3; i++) cycle();
    expect(row(0).isEmpty() && output("ASCII") == 65, "Run=0 preserves queued data through clock cycles");
    input("Run", 1); cycle();
    expect(row(0).equals("A") && output("ASCII") == 66, "one cycle transfers exactly one character");
    cycle();
    expect(row(0).equals("AB") && output("Available") == 0, "second cycle drains second character");
    for (int i = 0; i < 3; i++) cycle();
    expect(row(0).equals("AB"), "empty queue never duplicates terminal output");
    enqueue("C"); input("Clear", 1);
    expect(row(0).isEmpty(), "Clear asynchronously clears TTY");
    expect(output("Transfer") == 0 && output("KeyboardClear") == 0, "Clear suppresses transfer but preserves host buffer");
    cycle(); cycle();
    expect(output("ASCII") == 67 && output("Available") == 1, "clear-held cycles do not consume character");
    input("Clear", 0); cycle();
    expect(row(0).equals("C"), "queued character survives clear and resumes");
    enqueue("D"); input("Reset", 1);
    expect(row(0).isEmpty() && output("Available") == 0, "Reset clears both actual host devices");
    cycle(); cycle();
    expect(row(0).isEmpty() && output("Available") == 0, "reset dominates enabled clocks");
    input("Reset", 0);
    enqueue("E\nF"); cycle(); cycle(); cycle();
    expect(row(0).equals("E") && row(1).equals("F"), "newline is processed by native TTY");
    enqueue("G");
    state.getPropagator().propagate(); state.getPropagator().propagate();
    expect(row(1).equals("F") && output("Available") == 1, "paused clocks retain input without output");
    cycle();
    expect(row(1).equals("FG"), "resume transfers paused input once");
    enqueue("\b!"); cycle(); cycle();
    expect(row(1).equals("F!"), "native TTY handles backspace then character");
    reset(); input("Run", 0);
    enqueue("K".repeat(32) + "Z");
    input("Run", 1);
    for (int i = 0; i < 33; i++) cycle();
    expect(row(0).equals("K".repeat(32)) && row(1).isEmpty() && output("Available") == 0,
        "configured 32-character host buffer silently drops excess input (known limitation)");
    System.out.println("Native Keyboard/TTY: " + checks + " assertions passed (hold, exact transfer, clear/reset, pause/resume, controls, finite host buffer).");
  }

  public static void main(String[] args) {
    try {
      if (args.length != 1) throw new IllegalArgumentException("Usage: M0TextSmoke circuits/bitwright.circ");
      var file = new Loader(null).openLogisimFile(new File(args[0]));
      var project = new Project(file);
      try {
        new M0TextSmoke(CircuitState.createRootState(project, file.getMainCircuit(), Thread.currentThread())).test();
      } finally {
        project.getSimulator().shutDown();
      }
      System.exit(0);
    } catch (Exception | AssertionError failure) {
      failure.printStackTrace();
      System.exit(1);
    }
  }
}
