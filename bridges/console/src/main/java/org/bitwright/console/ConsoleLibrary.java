package org.bitwright.console;
import com.cburch.logisim.tools.AddTool;
import com.cburch.logisim.tools.Library;
import com.cburch.logisim.tools.Tool;
import java.util.List;
public final class ConsoleLibrary extends Library {
  public static final String _ID = "BitwrightConsoleHost";
  private final List<Tool> tools = List.of(new AddTool(new ConsoleHost()));
  @Override public String getDisplayName() { return "Bitwright console host adapter"; }
  @Override public List<? extends Tool> getTools() { return tools; }
}
