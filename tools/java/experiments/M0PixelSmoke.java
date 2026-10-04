import com.cburch.logisim.circuit.Analyze;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.HashMap;
import java.util.Map;

/** Runs the actual native stock-video bus. Private image reflection is pinned to Logisim 5.0.0. */
public final class M0PixelSmoke {
  private final CircuitState state;
  private final Map<String, Instance> inputs = new HashMap<>();
  private final Component video;

  private M0PixelSmoke(CircuitState state) {
    this.state = state;
    for (var entry : Analyze.getPinLabels(state.getCircuit()).entrySet()) {
      if (Pin.FACTORY.isInputPin(entry.getKey())) inputs.put(entry.getValue(), entry.getKey());
    }
    video = state.getCircuit().getNonWires().stream()
        .filter(c -> c.getFactory().getName().equals("RGB Video"))
        .findFirst().orElseThrow();
    state.getPropagator().propagate();
  }

  private void input(String name, int value) {
    var pin = inputs.get(name);
    if (pin == null) throw new IllegalStateException("Missing input " + name);
    Pin.FACTORY.driveInputPin(state.getInstanceState(pin), Value.createKnown(Pin.FACTORY.getWidth(pin), value));
    state.markComponentAsDirty(pin.getComponent());
    state.getPropagator().propagate();
  }

  private void cycle() {
    for (int i = 0; i < 2; i++) {
      state.getPropagator().toggleClocks();
      state.getPropagator().propagate();
    }
  }

  private int pixel(int x, int y) throws Exception {
    var data = state.getData(video);
    var field = data.getClass().getDeclaredField("img");
    field.setAccessible(true);
    return ((BufferedImage) field.get(data)).getRGB(x, y) & 0xffffff;
  }

  private void expect(int x, int y, int expected, String context) throws Exception {
    int actual = pixel(x, y);
    if (actual != expected) throw new AssertionError(context + ": pixel (" + x + "," + y + ") = "
        + Integer.toHexString(actual) + ", expected " + Integer.toHexString(expected));
  }

  private void run() throws Exception {
    input("Reset", 1);
    input("Reset", 0);
    expect(0, 0, 0, "reset");
    input("Plot", 1);
    for (int color = 1; color < 8; color++) {
      int x = color == 7 ? 127 : color - 1;
      int y = color == 7 ? 127 : 0;
      input("X", x); input("Y", y); input("Color", color);
      cycle();
      int rgb = ((color & 4) != 0 ? 0xff0000 : 0) | ((color & 2) != 0 ? 0xff00 : 0) | ((color & 1) != 0 ? 0xff : 0);
      expect(x, y, rgb, "write color " + color);
    }
    input("Plot", 0);
    input("Color", 0);
    cycle();
    expect(127, 127, 0xffffff, "hold with Plot=0");
    input("Clear", 1);
    expect(0, 0, 0, "asynchronous clear at origin");
    expect(127, 127, 0, "asynchronous clear at far corner");
    input("Clear", 0);
    input("Plot", 1);
    input("Color", 4);
    cycle();
    expect(127, 127, 0xff0000, "write after clear");
    input("Reset", 1);
    expect(127, 127, 0, "reset priority");
    System.out.println("Native RGB Video: 13 pixel assertions passed (all colors, corners, hold, clear, reset).");
  }

  public static void main(String[] args) {
    try {
      if (args.length != 1) throw new IllegalArgumentException("Usage: M0PixelSmoke circuits/bitwright.circ");
      var file = new Loader(null).openLogisimFile(new File(args[0]));
      var project = new Project(file);
      try {
        new M0PixelSmoke(CircuitState.createRootState(project, file.getMainCircuit(), Thread.currentThread())).run();
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
