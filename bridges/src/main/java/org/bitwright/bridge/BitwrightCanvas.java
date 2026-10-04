package org.bitwright.bridge;

import com.cburch.logisim.data.BitWidth;
import com.cburch.logisim.data.Bounds;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.instance.InstanceFactory;
import com.cburch.logisim.instance.InstancePainter;
import com.cburch.logisim.instance.InstancePoker;
import com.cburch.logisim.instance.InstanceState;
import com.cburch.logisim.instance.Port;
import com.cburch.logisim.util.StringUtil;
import java.awt.Color;
import java.awt.Font;
import java.awt.event.MouseEvent;

/** A retained host canvas and mouse adapter, with no CPU, MMIO, or machine FIFO. */
public final class BitwrightCanvas extends InstanceFactory {
  public static final String _ID = "BitwrightCanvas";
  static final int CLK = 0, RESET = 1, PLOT = 2, CLEAR = 3, X = 4, Y = 5,
      COLOR = 6, ACK = 7, OV_CLEAR = 8, VALID = 9, MOUSE_X = 10, MOUSE_Y = 11,
      BUTTONS = 12, OVERFLOW = 13;
  static final int IMAGE_X = 20, IMAGE_Y = 20;

  public BitwrightCanvas() {
    super(_ID, StringUtil.constantGetter("Bitwright host canvas"));
    setOffsetBounds(Bounds.create(0, 0, 180, 200));
    Port[] ports = {
      port(0, 20, Port.INPUT, 1, "CLK: controls commit on falling edge"),
      port(0, 40, Port.INPUT, 1, "RESET: asynchronous clear of image and host events"),
      port(0, 60, Port.INPUT, 1, "PLOT: write one RGB pixel"),
      port(0, 80, Port.INPUT, 1, "CLEAR: black image; takes priority over PLOT"),
      port(0, 100, Port.INPUT, 7, "X: pixel column 0..127"),
      port(0, 120, Port.INPUT, 7, "Y: pixel row 0..127"),
      port(0, 140, Port.INPUT, 3, "COLOR: RGB bits, red=4 green=2 blue=1"),
      port(0, 160, Port.INPUT, 1, "ACK: consume one presented event on falling edge"),
      port(0, 180, Port.INPUT, 1, "OV_CLEAR: clear host overflow on falling edge"),
      port(180, 20, Port.OUTPUT, 1, "VALID: event packet available"),
      port(180, 40, Port.OUTPUT, 7, "MOUSE_X: head event column"),
      port(180, 60, Port.OUTPUT, 7, "MOUSE_Y: head event row"),
      port(180, 80, Port.OUTPUT, 3, "BUTTONS: bit0 primary, bit1 secondary, bit2 middle"),
      port(180, 100, Port.OUTPUT, 1, "OVERFLOW: host queue dropped one or more new events")
    };
    setPorts(ports);
    setInstancePoker(Poker.class);
  }

  private static Port port(int x, int y, String type, int bits, String tip) {
    Port port = new Port(x, y, type, bits);
    port.setToolTip(StringUtil.constantGetter(tip));
    return port;
  }

  static CanvasState data(InstanceState state) {
    CanvasState data = (CanvasState) state.getData();
    if (data == null) {
      data = new CanvasState();
      state.setData(data);
    }
    return data;
  }

  private static int number(InstanceState state, int port) {
    Value value = state.getPortValue(port);
    return value.isFullyDefined() ? (int) value.toLongValue() : -1;
  }

  private static boolean high(InstanceState state, int port) {
    return Value.TRUE.equals(state.getPortValue(port));
  }

  @Override
  public void propagate(InstanceState state) {
    CanvasState data = data(state);
    data.advance(number(state, CLK), high(state, RESET), high(state, PLOT), high(state, CLEAR),
        number(state, X), number(state, Y), number(state, COLOR),
        // A host event can arrive in the same propagation step as a falling edge.
        // Only acknowledge a packet already advertised on the circuit-facing pins;
        // otherwise its first publication could also discard it before the circuit
        // has had a chance to observe VALID and the packet coordinates.
        high(state, ACK) && high(state, VALID), high(state, OV_CLEAR));
    CanvasState.Output output = data.output();
    CanvasState.Packet packet = output.head();
    state.setPort(VALID, packet == null ? Value.FALSE : Value.TRUE, 1);
    state.setPort(MOUSE_X, Value.createKnown(BitWidth.create(7), packet == null ? 0 : packet.x()), 1);
    state.setPort(MOUSE_Y, Value.createKnown(BitWidth.create(7), packet == null ? 0 : packet.y()), 1);
    state.setPort(BUTTONS, Value.createKnown(BitWidth.create(3), packet == null ? 0 : packet.buttons()), 1);
    state.setPort(OVERFLOW, output.overflow() ? Value.TRUE : Value.FALSE, 1);
  }

  @Override
  public void paintInstance(InstancePainter painter) {
    var graphics = painter.getGraphics();
    var bounds = painter.getBounds();
    int x = bounds.getX(), y = bounds.getY();
    graphics.setColor(new Color(238, 241, 246));
    graphics.fillRect(x, y, 180, 200);
    graphics.setColor(Color.DARK_GRAY);
    graphics.drawRect(x, y, 180, 200);
    graphics.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 10));
    graphics.drawString("BITWRIGHT HOST CANVAS", x + 20, y + 13);
    CanvasState data = painter.getShowState() ? (CanvasState) painter.getData() : null;
    if (data == null) {
      graphics.setColor(Color.BLACK);
      graphics.fillRect(x + IMAGE_X, y + IMAGE_Y, 128, 128);
    } else {
      data.paint(graphics, x + IMAGE_X, y + IMAGE_Y);
    }
    graphics.setColor(Color.DARK_GRAY);
    graphics.drawRect(x + IMAGE_X - 1, y + IMAGE_Y - 1, 129, 129);
    graphics.drawString("Poke: click / drag", x + 20, y + 162);
    CanvasState.Output output = data == null ? null : data.output();
    graphics.drawString("Host queue " + (output == null ? 0 : output.queued()) + "/256", x + 20, y + 176);
    if (output != null && output.overflow()) {
      graphics.setColor(Color.RED);
      graphics.drawString("OVERFLOW: reset input", x + 20, y + 190);
    } else {
      graphics.drawString("128x128  RGB 3-bit", x + 20, y + 190);
    }
    painter.drawPorts();
  }

  public static final class Poker extends InstancePoker {
    public Poker() {}

    @Override
    public Bounds getBounds(InstancePainter painter) {
      var location = painter.getLocation();
      return Bounds.create(location.getX() + IMAGE_X, location.getY() + IMAGE_Y, 128, 128);
    }

    @Override
    public boolean init(InstanceState state, MouseEvent event) {
      var location = state.getInstance().getLocation();
      int x = event.getX() - location.getX() - IMAGE_X;
      int y = event.getY() - location.getY() - IMAGE_Y;
      return x >= 0 && x < 128 && y >= 0 && y < 128;
    }

    private void capture(InstanceState state, MouseEvent event, int buttons) {
      var location = state.getInstance().getLocation();
      data(state).capture(event.getX() - location.getX() - IMAGE_X,
          event.getY() - location.getY() - IMAGE_Y, buttons);
      state.fireInvalidated();
    }

    private static int buttonBit(int button) {
      return switch (button) {
        case MouseEvent.BUTTON1 -> 1;
        case MouseEvent.BUTTON3 -> 2;
        case MouseEvent.BUTTON2 -> 4;
        default -> 0;
      };
    }

    private static int heldButtons(MouseEvent event) {
      int modifiers = event.getModifiersEx();
      return ((modifiers & MouseEvent.BUTTON1_DOWN_MASK) != 0 ? 1 : 0)
          | ((modifiers & MouseEvent.BUTTON3_DOWN_MASK) != 0 ? 2 : 0)
          | ((modifiers & MouseEvent.BUTTON2_DOWN_MASK) != 0 ? 4 : 0);
    }

    @Override
    public void mousePressed(InstanceState state, MouseEvent event) {
      // InstancePokerAdapter first synthesizes a metadata-free press. PokeTool
      // immediately follows it with the original event. Ignore the synthetic one
      // so there is exactly one packet per physical transition.
      if (event.getButton() == MouseEvent.NOBUTTON) return;
      capture(state, event, heldButtons(event) | buttonBit(event.getButton()));
    }

    @Override
    public void mouseDragged(InstanceState state, MouseEvent event) {
      capture(state, event, heldButtons(event));
    }

    @Override
    public void mouseReleased(InstanceState state, MouseEvent event) {
      capture(state, event, heldButtons(event) & ~buttonBit(event.getButton()));
    }

    @Override
    public void stopEditing(InstanceState state) {
      data(state).releaseAll();
      state.fireInvalidated();
    }
  }
}
