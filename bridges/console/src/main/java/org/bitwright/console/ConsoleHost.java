package org.bitwright.console;

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
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import javax.swing.JFileChooser;
import javax.swing.JOptionPane;
import javax.swing.filechooser.FileNameExtensionFilter;

/** Captures ASCII and presents raw pixels. No font, CPU, MMIO, cursor, or scrolling. */
public final class ConsoleHost extends InstanceFactory {
  public static final String _ID = "ConsoleHost";
  public static final int CLK=0, RESET=1, ACK=2, DRAW=3, COLUMN=4, ROW=5, BITMAP=6, VALID=7, ASCII=8, OVERFLOW=9;
  public ConsoleHost() {
    super(_ID, StringUtil.constantGetter("ASCII keyboard / raw pixel monitor"));
    setOffsetBounds(Bounds.create(0, 0, 380, 290));
    setPorts(new Port[] {
      port(0,20,Port.INPUT,1,"Clock: input ack rising; pixel word falling"),
      port(0,50,Port.INPUT,1,"Reset host queue and pixels"),
      port(0,80,Port.INPUT,1,"Acknowledge the currently advertised input byte"),
      port(0,110,Port.INPUT,1,"Write eight raw pixels on falling edge"),
      port(0,140,Port.INPUT,6,"Pixel-word column (0..39)"),
      port(0,170,Port.INPUT,8,"Pixel row (0..191)"),
      port(0,200,Port.INPUT,8,"Pixel bits, bit0 is leftmost"),
      port(380,30,Port.OUTPUT,1,"ASCII byte available"),
      port(380,60,Port.OUTPUT,7,"ASCII head, stable until acknowledged"),
      port(380,90,Port.OUTPUT,1,"Host queue overflow")
    });
    setInstancePoker(Poker.class);
  }
  private static Port port(int x,int y,String type,int width,String tip) {
    var p=new Port(x,y,type,width); p.setToolTip(StringUtil.constantGetter(tip)); return p;
  }
  public static ConsoleState data(InstanceState state) {
    var data=(ConsoleState)state.getData();
    if(data==null){data=new ConsoleState();state.setData(data);} return data;
  }
  private static boolean high(InstanceState s,int p){return Value.TRUE.equals(s.getPortValue(p));}
  private static int number(InstanceState s,int p){var v=s.getPortValue(p);return v.isFullyDefined()?(int)v.toLongValue():-1;}
  @Override public void propagate(InstanceState state) {
    var d=data(state);
    d.advance(number(state,CLK),high(state,RESET),high(state,ACK)&&high(state,VALID),high(state,DRAW),number(state,COLUMN),number(state,ROW),number(state,BITMAP));
    int head=d.head();
    state.setPort(VALID,head<0?Value.FALSE:Value.TRUE,1);
    state.setPort(ASCII,Value.createKnown(BitWidth.create(7),Math.max(0,head)),1);
    state.setPort(OVERFLOW,d.overflow()?Value.TRUE:Value.FALSE,1);
  }
  @Override public void paintInstance(InstancePainter p) {
    var g=p.getGraphics();var b=p.getBounds();int x=b.getX(),y=b.getY();
    g.setColor(new Color(232,237,242));g.fillRect(x,y,380,290);g.setColor(Color.DARK_GRAY);g.drawRect(x,y,380,290);
    g.setFont(new Font(Font.MONOSPACED,Font.BOLD,12));g.drawString("BITWRIGHT / ASCII + RAW PIXELS",x+20,y+18);
    var d=p.getShowState()?(ConsoleState)p.getData():null;
    if(d!=null)d.paint(g,x+30,y+30);else{g.setColor(Color.BLACK);g.fillRect(x+30,y+30,320,192);}
    g.setColor(Color.DARK_GRAY);g.drawRect(x+29,y+29,321,193);
    g.setFont(new Font(Font.MONOSPACED,Font.PLAIN,11));
    g.drawString("Click screen to type. Esc / Enter / Backspace",x+20,y+240);
    g.drawRect(x+20,y+249,160,24);g.drawString("Load ASCII .mon file",x+25,y+265);
    g.drawString("Queued: "+(d==null?0:d.queued()),x+195,y+265);
    if(d!=null&&d.overflow()){g.setColor(Color.RED);g.drawString("INPUT OVERFLOW",x+220,y+283);}
    p.drawPorts();
  }
  public static final class Poker extends InstancePoker {
    @Override public Bounds getBounds(InstancePainter p){var l=p.getLocation();return Bounds.create(l.getX()+20,l.getY()+25,340,250);}
    @Override public boolean init(InstanceState s,MouseEvent e){return true;}
    @Override public void mousePressed(InstanceState s,MouseEvent e) {
      if(e.getButton()==MouseEvent.NOBUTTON)return;
      var l=s.getInstance().getLocation();int x=e.getX()-l.getX(),y=e.getY()-l.getY();
      if(x<20||x>180||y<249||y>273)return;
      var chooser=new JFileChooser();chooser.setDialogTitle("Feed ASCII program load records to Bitwright");
      chooser.setFileFilter(new FileNameExtensionFilter("Monitor input (*.mon, *.txt)","mon","txt"));
      if(chooser.showOpenDialog(e.getComponent())==JFileChooser.APPROVE_OPTION){
        try{data(s).load(chooser.getSelectedFile().toPath());s.fireInvalidated();}
        catch(Exception failure){JOptionPane.showMessageDialog(e.getComponent(),failure.getMessage(),"Cannot load input",JOptionPane.ERROR_MESSAGE);}
      }
    }
    @Override public void keyTyped(InstanceState s,KeyEvent e){if(data(s).capture(e.getKeyChar())){s.fireInvalidated();e.consume();}}
  }
}
