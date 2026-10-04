package org.bitwright.bridge;

import com.cburch.logisim.instance.InstanceData;
import java.awt.Graphics;
import java.awt.image.BufferedImage;
import java.util.ArrayDeque;
import java.util.Arrays;

/** Host pixels and a bounded host-event handoff, never CPU-visible device logic. */
final class CanvasState implements InstanceData {
  static final int SIZE = 128;
  static final int CAPACITY = 256;
  record Packet(int x, int y, int buttons) {}
  record Output(Packet head, boolean overflow, int queued) {}

  private int[] pixels = new int[SIZE * SIZE];
  private ArrayDeque<Packet> events = new ArrayDeque<>();
  private int lastClock = -1;
  private boolean overflow;
  private boolean resetActive;
  private int lastX;
  private int lastY;
  private int buttons;

  CanvasState() {
    Arrays.fill(pixels, 0xff000000);
  }

  private static int clamp(int value) {
    return Math.max(0, Math.min(SIZE - 1, value));
  }

  /** UI calls serialize with propagation and cloning; the front packet never mutates. */
  synchronized void capture(int x, int y, int nextButtons) {
    if (resetActive) return;
    lastX = clamp(x);
    lastY = clamp(y);
    buttons = nextButtons & 7;
    if (events.size() == CAPACITY) {
      overflow = true; // Drop newest. Existing packet order and the presented head are stable.
    } else {
      events.addLast(new Packet(lastX, lastY, buttons));
    }
  }

  synchronized void releaseAll() {
    if (buttons != 0) capture(lastX, lastY, 0);
  }

  /** Controls commit only on a known 1->0 edge. Reset is asynchronous and dominant. */
  synchronized void advance(int clock, boolean reset, boolean plot, boolean clear,
                            int x, int y, int color, boolean ack, boolean clearOverflow) {
    boolean falling = lastClock == 1 && clock == 0;
    lastClock = clock;
    resetActive = reset;
    if (reset) {
      Arrays.fill(pixels, 0xff000000);
      events.clear();
      overflow = false;
      lastX = lastY = buttons = 0;
      return;
    }
    if (!falling) return;
    if (ack) events.pollFirst();
    if (clearOverflow) overflow = false;
    if (clear) {
      Arrays.fill(pixels, 0xff000000);
    } else if (plot && x >= 0 && x < SIZE && y >= 0 && y < SIZE && color >= 0 && color < 8) {
      // Same RGB ordering as stock 8-Color RGB: R bit2, G bit1, B bit0.
      pixels[y * SIZE + x] = 0xff000000
          | ((color & 4) != 0 ? 0x00ff0000 : 0)
          | ((color & 2) != 0 ? 0x0000ff00 : 0)
          | ((color & 1) != 0 ? 0x000000ff : 0);
    }
  }

  synchronized Output output() {
    return new Output(events.peekFirst(), overflow, events.size());
  }

  synchronized int pixel(int x, int y) {
    return pixels[y * SIZE + x];
  }

  synchronized void paint(Graphics graphics, int x, int y) {
    BufferedImage image = new BufferedImage(SIZE, SIZE, BufferedImage.TYPE_INT_RGB);
    image.setRGB(0, 0, SIZE, SIZE, pixels, 0, SIZE);
    graphics.drawImage(image, x, y, null);
  }

  @Override
  public synchronized CanvasState clone() {
    CanvasState copy = new CanvasState();
    copy.pixels = pixels.clone();
    copy.events = new ArrayDeque<>(events); // Packets are immutable records.
    copy.lastClock = lastClock;
    copy.overflow = overflow;
    copy.resetActive = resetActive;
    copy.lastX = lastX;
    copy.lastY = lastY;
    copy.buttons = buttons;
    return copy;
  }
}
