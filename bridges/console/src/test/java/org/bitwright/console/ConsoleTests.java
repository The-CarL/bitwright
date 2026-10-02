package org.bitwright.console;
import java.nio.file.Files;
public final class ConsoleTests {
  private static int checks;
  private static void expect(boolean value,String why){checks++;if(!value)throw new AssertionError(why);}
  public static void main(String[] args)throws Exception{
    var d=new ConsoleState();d.advance(0,false,false,false,0,0,0);
    d.capture('A');d.capture('B');d.advance(0,false,true,false,0,0,0);
    expect(d.head()=='A',"paused host input stays stable");
    d.advance(1,false,true,false,0,0,0);expect(d.head()=='B',"one rising edge consumes one character");
    d.advance(1,false,true,false,0,0,0);expect(d.head()=='B',"same edge never consumes twice");
    d.advance(0,false,false,true,2,3,0x81);expect(d.pixel(16,3)&&d.pixel(23,3)&&!d.pixel(17,3),"raw pixel words have specified bit order");
    var copy=d.clone();copy.capture('C');expect(d.queued()==1&&copy.queued()==2,"cloned circuit states have independent input");
    d.advance(1,true,false,false,0,0,0);expect(d.queued()==0&&!d.pixel(16,3),"reset clears queue and frame");
    var file=Files.createTempFile("bitwright-load-",".mon");
    try{Files.writeString(file,"0200: A9 41\r\n0200R\n");d.load(file);expect(d.queued()==18,"file CRLF normalized without double enter");
      expect(d.head()=='0',"loader leaves characters unparsed");d.clearQueue();Files.write(file,new byte[]{(byte)255});
      try{d.load(file);throw new AssertionError("non-ASCII accepted");}catch(java.io.IOException expected){expect(d.queued()==0,"invalid file has no partial input");}
    }finally{Files.deleteIfExists(file);}
    for(int i=0;i<ConsoleState.CAPACITY;i++)d.capture('X');expect(!d.capture('Y')&&d.overflow(),"host queue has explicit finite overflow");
    d.clearQueue();expect(d.capture(27)&&d.capture(3)&&d.capture(8)&&d.capture(13),"Escape Ctrl-C backspace Enter are captured");
    System.out.println("Console host adapter: "+checks+" assertions passed.");
  }
}
