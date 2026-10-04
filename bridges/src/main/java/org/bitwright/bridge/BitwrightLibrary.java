package org.bitwright.bridge;

import com.cburch.logisim.tools.AddTool;
import com.cburch.logisim.tools.Library;
import com.cburch.logisim.tools.Tool;
import java.util.List;

/** Entry point loaded by Logisim-evolution's native JAR library mechanism. */
public final class BitwrightLibrary extends Library {
  public static final String _ID = "BitwrightHostBridge";
  private final List<Tool> tools = List.of(new AddTool(new BitwrightCanvas()));

  public BitwrightLibrary() {}

  @Override
  public String getDisplayName() {
    return "Bitwright host bridge (M0)";
  }

  @Override
  public List<? extends Tool> getTools() {
    return tools;
  }
}
