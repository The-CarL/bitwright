import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.ComponentDrawContext;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.proj.Project;
import java.awt.Color;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import javax.swing.JPanel;

/** Development artifact renderer using Logisim's native component painters, never a desktop screenshot. */
public final class RenderCircuit {
  public static void main(String[] args) {
    try {
      render(args);
    } catch (Exception failure) {
      failure.printStackTrace();
      System.exit(1);
    }
  }

  private static void render(String[] args) throws Exception {
    if (args.length != 3) {
      throw new IllegalArgumentException("Usage: RenderCircuit input.circ circuitName output.png");
    }
    var loader = new Loader(null);
    var file = loader.openLogisimFile(new File(args[0]));
    var circuit = file.getCircuit(args[1]);
    if (circuit == null) throw new IllegalArgumentException("Missing circuit: " + args[1]);
    var project = new Project(file);
    try {
      var state = CircuitState.createRootState(project, circuit, Thread.currentThread());
      state.getPropagator().propagate();
      for (var component : circuit.getNonWires()) {
        for (var end : component.getEnds()) {
          if (state.getValue(end.getLocation()).isErrorValue()) {
            throw new IllegalStateException("Error signal at " + end.getLocation() + " on " + component.getFactory().getName());
          }
        }
      }
      var measure = new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB);
      var measurementGraphics = measure.createGraphics();
      var bounds = circuit.getBounds(measurementGraphics).expand(25);
      measurementGraphics.dispose();
      var image = new BufferedImage(bounds.getWidth(), bounds.getHeight(), BufferedImage.TYPE_INT_RGB);
      var base = image.createGraphics();
      base.setColor(Color.WHITE);
      base.fillRect(0, 0, image.getWidth(), image.getHeight());
      var graphics = (java.awt.Graphics2D) base.create();
      graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
      graphics.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
      graphics.translate(-bounds.getX(), -bounds.getY());
      circuit.draw(new ComponentDrawContext(new JPanel(), circuit, state, base, graphics, false), null);
      graphics.dispose();
      base.dispose();
      var destination = new File(args[2]);
      if (destination.getParentFile() != null) destination.getParentFile().mkdirs();
      if (!ImageIO.write(image, "png", destination)) throw new IllegalStateException("No PNG writer");
      System.out.printf("Rendered %s: %d x %d -> %s%n", args[1], image.getWidth(), image.getHeight(), args[2]);
    } finally {
      project.getSimulator().shutDown();
    }
    System.exit(0);
  }
}
