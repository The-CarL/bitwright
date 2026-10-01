package org.bitwright.bridge;

import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.data.Attribute;
import com.cburch.logisim.data.AttributeSet;
import com.cburch.logisim.data.BitWidth;
import com.cburch.logisim.data.Location;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.instance.Instance;
import com.cburch.logisim.instance.InstanceData;
import com.cburch.logisim.instance.InstanceFactory;
import com.cburch.logisim.instance.InstanceState;
import com.cburch.logisim.instance.Port;
import com.cburch.logisim.proj.Project;
import java.awt.Canvas;
import java.awt.event.MouseEvent;
import java.util.Arrays;

/** Dependency-free contract tests using the actual pinned simulator API. */
public final class BridgeTests {
  private static int checks;
  private static void check(boolean condition, String description) {
    checks++;
    if (!condition) throw new AssertionError(description);
  }
  private static void idle(CanvasState state, int clock, boolean ack) {
    state.advance(clock, false, false, false, 0, 0, 0, ack, false);
  }
  private static void acknowledge(CanvasState state) {
    idle(state, 1, true);
    idle(state, 0, true);
  }
  private static void plot(CanvasState state, int x, int y, int color) {
    state.advance(1, false, true, false, x, y, color, false, false);
    state.advance(0, false, true, false, x, y, color, false, false);
  }
  private static void reset(CanvasState state) {
    state.advance(0, true, true, true, 5, 5, 7, true, true);
  }

  private static void pixelsAndEdges() {
    CanvasState state = new CanvasState();
    check(state.pixel(0, 0) == 0xff000000, "starts black");
    state.advance(0, false, true, false, 0, 0, 7, false, false);
    check(state.pixel(0, 0) == 0xff000000, "initial low is not a falling edge");
    int[] palette = {0xff000000, 0xff0000ff, 0xff00ff00, 0xff00ffff,
        0xffff0000, 0xffff00ff, 0xffffff00, 0xffffffff};
    for (int color = 0; color < 8; color++) {
      plot(state, color, color, color);
      check(state.pixel(color, color) == palette[color], "RGB palette " + color);
    }
    plot(state, 127, 127, 4);
    check(state.pixel(127, 127) == 0xffff0000, "last coordinate is addressable");
    state.advance(0, false, true, false, 127, 127, 2, false, false);
    check(state.pixel(127, 127) == 0xffff0000, "duplicate propagation does not plot twice");
    idle(state, 1, false);
    idle(state, -1, false);
    state.advance(0, false, true, false, 127, 127, 2, false, false);
    check(state.pixel(127, 127) == 0xffff0000, "unknown clock breaks edge recognition");
    plot(state, -1, 0, 7);
    plot(state, 0, 128, 7);
    plot(state, 0, 0, -1);
    check(state.pixel(0, 0) == 0xff000000, "invalid plot operands ignored");
    idle(state, 1, false);
    state.advance(0, false, true, true, 127, 127, 7, false, false);
    check(state.pixel(127, 127) == 0xff000000, "clear dominates plot");
    plot(state, 4, 5, 7);
    reset(state);
    check(state.pixel(4, 5) == 0xff000000, "reset clears image without edge");
    check(state.pixel(5, 5) == 0xff000000, "reset suppresses plot");
  }

  private static void queueAndReset() {
    CanvasState state = new CanvasState();
    state.capture(-10, 150, 1);
    state.capture(50, 60, 0);
    check(state.output().head().equals(new CanvasState.Packet(0, 127, 1)), "coordinates clamp");
    idle(state, 0, true);
    idle(state, 1, true);
    check(state.output().queued() == 2, "ack does not consume at low initialization or rising edge");
    idle(state, 0, true);
    check(state.output().head().equals(new CanvasState.Packet(50, 60, 0)), "ack consumes one packet");
    idle(state, 0, true);
    check(state.output().queued() == 1, "repeated low propagation does not consume twice");
    acknowledge(state);
    check(state.output().head() == null, "last ack empties queue");
    acknowledge(state);
    check(state.output().queued() == 0, "ack on empty harmless");
    state.capture(12, 34, 1);
    var before = state.output().head();
    for (int i = 0; i < 50; i++) {
      state.capture(i, i, 1);
      idle(state, i % 2, false);
      check(state.output().head().equals(before), "head stable until acknowledgement");
    }
    reset(state);
    state.capture(3, 4, 1);
    check(state.output().queued() == 0 && !state.output().overflow(), "reset clears queue and suppresses input while held");
    idle(state, 0, false);
    state.capture(3, 4, 1);
    state.releaseAll();
    state.releaseAll();
    check(state.output().queued() == 2, "focus-stop synthesis adds one release");
    acknowledge(state);
    check(state.output().head().buttons() == 0, "focus-stop release has no pressed buttons");
  }

  private static void overflowAndClone() {
    CanvasState state = new CanvasState();
    for (int i = 0; i < CanvasState.CAPACITY; i++) state.capture(i % 128, 4, i % 2);
    check(!state.output().overflow(), "exact capacity is not overflow");
    state.capture(99, 99, 0);
    check(state.output().queued() == 256 && state.output().overflow(), "newest packet dropped with explicit overflow");
    for (int i = 0; i < 256; i++) {
      check(state.output().head().equals(new CanvasState.Packet(i % 128, 4, i % 2)), "overflow preserves retained packet order");
      acknowledge(state);
    }
    check(state.output().head() == null && state.output().overflow(), "overflow sticky after drain");
    state.advance(1, false, false, false, 0, 0, 0, false, true);
    check(state.output().overflow(), "clear overflow also edge sensitive");
    state.advance(0, false, false, false, 0, 0, 0, false, true);
    check(!state.output().overflow(), "overflow clear commits on falling edge");
    state.capture(1, 2, 1);
    plot(state, 3, 4, 7);
    CanvasState clone = state.clone();
    acknowledge(clone);
    plot(clone, 3, 4, 2);
    check(state.output().queued() == 1, "clone event queue independent");
    check(state.pixel(3, 4) == 0xffffffff && clone.pixel(3, 4) == 0xff00ff00, "clone image independent");
    clone.capture(6, 7, 0);
    check(state.output().head().x() == 1, "clone host capture independent");
  }

  private static final class FakeState implements InstanceState {
    final BitwrightCanvas factory = new BitwrightCanvas();
    final Instance instance = Instance.getInstanceFor(factory.createComponent(
        Location.create(200, 100, true), factory.createAttributeSet()));
    final Value[] values = new Value[14];
    InstanceData data;
    int invalidations;
    FakeState() { Arrays.fill(values, Value.FALSE); }
    void value(int index, int width, int value) { values[index] = Value.createKnown(BitWidth.create(width), value); }
    public void fireInvalidated() { invalidations++; }
    public AttributeSet getAttributeSet() { return instance.getAttributeSet(); }
    public <E> E getAttributeValue(Attribute<E> attr) { return getAttributeSet().getValue(attr); }
    public InstanceData getData() { return data; }
    public InstanceFactory getFactory() { return factory; }
    public Instance getInstance() { return instance; }
    public int getPortIndex(Port port) { return instance.getPorts().indexOf(port); }
    public Value getPortValue(int port) { return values[port]; }
    public Project getProject() { throw new UnsupportedOperationException(); }
    public int getTickCount() { return 0; }
    public boolean isCircuitRoot() { return true; }
    public boolean isPortConnected(int port) { return true; }
    public CircuitState createCircuitSubstateFor(Circuit circuit) { throw new UnsupportedOperationException(); }
    public void setData(InstanceData value) { data = value; }
    public void setPort(int port, Value value, int delay) { values[port] = value; }
    void propagate() { factory.propagate(this); }
  }
  private static MouseEvent mouse(int id, int x, int y) {
    // Deliberately no button metadata, matching Logisim's initial synthetic press.
    return new MouseEvent(new Canvas(), id, 0, 0, x, y, 1, false);
  }
  private static MouseEvent realMouse(int id, int x, int y, int modifiers, int button) {
    return new MouseEvent(new Canvas(), id, 0, modifiers, x, y, 1, false, button);
  }
  private static void adapterContract() {
    FakeState state = new FakeState();
    check(new BitwrightLibrary().getTool("BitwrightCanvas") != null, "JAR library exposes stable component ID");
    check(state.instance.getPortLocation(0).equals(Location.create(200, 120, true)), "CLK physical position");
    check(state.instance.getPortLocation(13).equals(Location.create(380, 200, true)), "overflow physical position");
    state.propagate();
    check(state.values[BitwrightCanvas.VALID].equals(Value.FALSE), "empty packet output invalid");
    BitwrightCanvas.Poker poker = new BitwrightCanvas.Poker();
    check(!poker.init(state, mouse(MouseEvent.MOUSE_PRESSED, 210, 110)), "outside image rejects poke");
    check(poker.init(state, mouse(MouseEvent.MOUSE_PRESSED, 220, 120)), "first image pixel accepts poke");
    poker.mousePressed(state, mouse(MouseEvent.MOUSE_PRESSED, 220, 120));
    check(BitwrightCanvas.data(state).output().queued() == 0, "synthetic initial press suppressed");
    poker.mousePressed(state, realMouse(MouseEvent.MOUSE_PRESSED, 220, 120,
        MouseEvent.BUTTON1_DOWN_MASK, MouseEvent.BUTTON1));
    poker.mouseDragged(state, realMouse(MouseEvent.MOUSE_DRAGGED, 600, -10,
        MouseEvent.BUTTON1_DOWN_MASK, MouseEvent.NOBUTTON));
    poker.mouseReleased(state, realMouse(MouseEvent.MOUSE_RELEASED, 600, -10, 0, MouseEvent.BUTTON1));
    state.propagate();
    check(state.values[BitwrightCanvas.VALID].equals(Value.TRUE), "host capture propagates valid");
    check(state.values[BitwrightCanvas.BUTTONS].toLongValue() == 1, "original press maps to primary bit");
    check(state.values[BitwrightCanvas.MOUSE_X].toLongValue() == 0, "coordinate translated to image origin");
    state.value(BitwrightCanvas.ACK, 1, 1);
    state.value(BitwrightCanvas.CLK, 1, 1); state.propagate();
    state.value(BitwrightCanvas.CLK, 1, 0); state.propagate();
    check(state.values[BitwrightCanvas.MOUSE_X].toLongValue() == 127
        && state.values[BitwrightCanvas.MOUSE_Y].toLongValue() == 0, "out-of-canvas drag clamps");
    state.propagate();
    check(BitwrightCanvas.data(state).output().queued() == 2, "adapter duplicate propagation preserves packet");
    state.value(BitwrightCanvas.CLK, 1, 1); state.propagate();
    state.value(BitwrightCanvas.CLK, 1, 0); state.propagate();
    check(state.values[BitwrightCanvas.BUTTONS].toLongValue() == 0, "release propagates zero buttons");
    poker.mousePressed(state, realMouse(MouseEvent.MOUSE_PRESSED, 250, 150,
        MouseEvent.BUTTON1_DOWN_MASK, MouseEvent.BUTTON1));
    poker.stopEditing(state);
    check(BitwrightCanvas.data(state).output().queued() == 3, "stopEditing enqueues release for held gesture");
    check(state.invalidations == 5, "all UI transitions request propagation/repaint");
    state.value(BitwrightCanvas.RESET, 1, 1); state.propagate();
    check(state.values[BitwrightCanvas.VALID].equals(Value.FALSE), "adapter reset clears outputs");
    check(state.values[BitwrightCanvas.MOUSE_X].getWidth() == 7, "mouse output width stable");
    state.value(BitwrightCanvas.RESET, 1, 0); state.propagate();
    poker.mousePressed(state, realMouse(MouseEvent.MOUSE_PRESSED, 250, 150,
        MouseEvent.BUTTON3_DOWN_MASK, MouseEvent.BUTTON3));
    check(BitwrightCanvas.data(state).output().head().buttons() == 2, "secondary metadata maps to bit1");
    acknowledge(BitwrightCanvas.data(state));
    poker.mousePressed(state, realMouse(MouseEvent.MOUSE_PRESSED, 250, 150,
        MouseEvent.BUTTON2_DOWN_MASK | MouseEvent.BUTTON3_DOWN_MASK, MouseEvent.BUTTON2));
    check(BitwrightCanvas.data(state).output().head().buttons() == 6, "middle press preserves held secondary");
    acknowledge(BitwrightCanvas.data(state));
    poker.mouseReleased(state, realMouse(MouseEvent.MOUSE_RELEASED, 250, 150,
        MouseEvent.BUTTON3_DOWN_MASK, MouseEvent.BUTTON2));
    check(BitwrightCanvas.data(state).output().head().buttons() == 2, "individual release preserves other button");
    acknowledge(BitwrightCanvas.data(state));
    poker.stopEditing(state);
    check(BitwrightCanvas.data(state).output().head().buttons() == 0, "stopEditing releases all buttons");
  }

  private static void firstArrivalAtFallingEdge() {
    FakeState state = new FakeState();
    state.value(BitwrightCanvas.CLK, 1, 1);
    state.value(BitwrightCanvas.ACK, 1, 1);
    state.propagate();
    check(state.values[BitwrightCanvas.VALID].equals(Value.FALSE), "idle queue advertises no packet");
    // Model AWT capture racing with the next clock propagation. No propagate()
    // occurs between this event and the falling edge, so the circuit has not yet
    // observed VALID or the event's coordinates despite ACK being held high.
    BitwrightCanvas.Poker poker = new BitwrightCanvas.Poker();
    poker.mousePressed(state, realMouse(MouseEvent.MOUSE_PRESSED, 232, 154,
        MouseEvent.BUTTON1_DOWN_MASK, MouseEvent.BUTTON1));
    state.value(BitwrightCanvas.CLK, 1, 0);
    state.propagate();
    check(BitwrightCanvas.data(state).output().queued() == 1, "same-edge first arrival is not acknowledged before publication");
    check(state.values[BitwrightCanvas.VALID].equals(Value.TRUE)
        && state.values[BitwrightCanvas.MOUSE_X].toLongValue() == 12
        && state.values[BitwrightCanvas.MOUSE_Y].toLongValue() == 34,
        "first arrival is presented with complete coordinates");
    state.propagate();
    check(BitwrightCanvas.data(state).output().queued() == 1, "publication retrigger does not consume without a new edge");
    // Once a head was advertised, one ACK edge consumes that head, not a later
    // event appended by AWT immediately before the acknowledgement.
    state.value(BitwrightCanvas.CLK, 1, 1); state.propagate();
    poker.mouseReleased(state, realMouse(MouseEvent.MOUSE_RELEASED, 233, 155, 0, MouseEvent.BUTTON1));
    state.value(BitwrightCanvas.CLK, 1, 0); state.propagate();
    check(BitwrightCanvas.data(state).output().queued() == 1
        && BitwrightCanvas.data(state).output().head().equals(new CanvasState.Packet(13, 35, 0)),
        "ACK consumes only the advertised head while a new event is appended");
    state.value(BitwrightCanvas.CLK, 1, 1); state.propagate();
    state.value(BitwrightCanvas.RESET, 1, 1);
    state.value(BitwrightCanvas.CLK, 1, 0); state.propagate();
    check(BitwrightCanvas.data(state).output().queued() == 0
        && state.values[BitwrightCanvas.VALID].equals(Value.FALSE),
        "reset remains dominant over publication and acknowledgement");
  }

  public static void main(String[] args) {
    pixelsAndEdges();
    queueAndReset();
    overflowAndClone();
    adapterContract();
    firstArrivalAtFallingEdge();
    System.out.println("BridgeTests: " + checks + " checks passed");
  }
}
