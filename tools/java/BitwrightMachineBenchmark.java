import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.proj.Project;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Bounded real-machine boot/idle benchmark; no memory injection or instruction emulation. */
public final class BitwrightMachineBenchmark {
  public static void main(String[] args) {
    try {
      var file = new Loader(null).openLogisimFile(new File(args[0]));
      var project = new Project(file);
      try {
        var machine = new MachineSmoke(CircuitState.createRootState(project, file.getMainCircuit(), Thread.currentThread()));
        machine.reset();
        int cycles = 3000, fetches = 0;
        long started = System.nanoTime();
        for (int i = 0; i < cycles; i++) {
          machine.cycle();
          if (machine.out("Sync") != 0) fetches++;
        }
        double seconds = (System.nanoTime() - started) / 1e9;
        int retired = fetches - 1; // First Fetch starts execution; each later Fetch follows a retired instruction.
        if (retired <= 0 || !machine.transcript.toString().contains("BITWRIGHT 6502")) throw new AssertionError("Benchmark did not boot firmware");
        String report = String.format(Locale.ROOT,
          "{\n  \"workload\":\"firmware boot then idle keyboard polling\",\n  \"cycles\":%d,\n  \"completed_instructions\":%d,\n  \"count_method\":\"Sync fetch boundaries minus initial entry, IRQ/NMI inactive\",\n  \"seconds\":%.6f,\n  \"cycles_per_second\":%.6f,\n  \"instructions_per_second\":%.6f,\n  \"gui_verified\":false\n}\n",
          cycles, retired, seconds, cycles / seconds, retired / seconds);
        var destination = Path.of(args[1]); Files.createDirectories(destination.getParent()); Files.writeString(destination, report);
        System.out.print(report);
      } finally { project.getSimulator().shutDown(); }
      System.exit(0);
    } catch (Exception | AssertionError failure) { failure.printStackTrace(); System.exit(1); }
  }
}
