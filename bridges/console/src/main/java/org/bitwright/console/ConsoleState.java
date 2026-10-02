package org.bitwright.console;

import com.cburch.logisim.instance.InstanceData;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.image.BufferedImage;
import java.nio.file.Files;
import java.nio.file.Path;
import java.io.IOException;
import java.util.ArrayDeque;

/** Host input queue and pixel store only. All terminal semantics live in .circ. */
public final class ConsoleState implements InstanceData, Cloneable {
  public static final int WIDTH = 320, HEIGHT = 192, CAPACITY = 65536;
  private ArrayDeque<Integer> input = new ArrayDeque<>();
  private BufferedImage pixels = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
  private boolean overflow;
  private int clock = -1;

  @Override public synchronized ConsoleState clone() {
    try {
      var result = (ConsoleState) super.clone();
      result.input = new ArrayDeque<>(input);
      result.pixels = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
      result.pixels.setRGB(0, 0, WIDTH, HEIGHT, pixels.getRGB(0, 0, WIDTH, HEIGHT, null, 0, WIDTH), 0, WIDTH);
      return result;
    } catch (CloneNotSupportedException impossible) { throw new AssertionError(impossible); }
  }

  /** ASCII capture; LF is normalized to the historical CR keyboard convention. */
  public synchronized boolean capture(int character) {
    if (character == 10) character = 13;
    if (!((character >= 32 && character <= 126) || character == 13 || character == 8 || character == 27 || character == 3 || character == 12)) return false;
    if (input.size() == CAPACITY) { overflow = true; return false; }
    input.addLast(character);
    return true;
  }

  /** Validates an entire ASCII stream before queuing it; never parses machine instructions. */
  public synchronized void load(Path file) throws IOException {
    if (Files.size(file) > CAPACITY) throw new IOException("Input text exceeds the 65536-byte host queue.");
    byte[] bytes = Files.readAllBytes(file);
    if (bytes.length > CAPACITY) throw new IOException("Input text exceeds the 65536-byte host queue.");
    ArrayDeque<Integer> pending = new ArrayDeque<>();
    int previous = -1;
    for (byte raw : bytes) {
      int value = raw & 255;
      if (value == 10 && previous == 13) { previous = value; continue; }
      if (value == 10) value = 13;
      if (!((value >= 32 && value <= 126) || value == 13 || value == 8 || value == 27 || value == 3 || value == 12))
        throw new IOException("Load files must contain printable ASCII and supported console controls.");
      pending.addLast(value); previous = raw & 255;
    }
    if (input.size() + pending.size() > CAPACITY) throw new IOException("Host queue is not empty enough for this file.");
    input.addAll(pending);
  }

  public synchronized int head() { return input.isEmpty() ? -1 : input.getFirst(); }
  public synchronized int queued() { return input.size(); }
  public synchronized boolean overflow() { return overflow; }
  public synchronized boolean pixel(int x, int y) { return (pixels.getRGB(x, y) & 0xffffff) != 0; }
  public synchronized void clearQueue() { input.clear(); overflow = false; }

  /** Rising edge acknowledges input; falling edge writes a packed group of eight pixels. */
  public synchronized void advance(int nextClock, boolean reset, boolean ack, boolean draw, int column, int y, int bitmap) {
    boolean rising = clock == 0 && nextClock == 1;
    boolean falling = clock == 1 && nextClock == 0;
    clock = nextClock;
    if (reset) {
      input.clear(); overflow = false;
      var g = pixels.createGraphics(); g.setColor(Color.BLACK); g.fillRect(0, 0, WIDTH, HEIGHT); g.dispose();
      return;
    }
    if (rising && ack && !input.isEmpty()) input.removeFirst();
    if (falling && draw && column >= 0 && column < 40 && y >= 0 && y < HEIGHT && bitmap >= 0) {
      for (int bit = 0; bit < 8; bit++) pixels.setRGB(column * 8 + bit, y, ((bitmap >>> bit) & 1) == 0 ? 0 : 0x77ff99);
    }
  }

  public synchronized void paint(Graphics graphics, int x, int y) { graphics.drawImage(pixels, x, y, null); }
}
