package top.cyqi.hook.mihome;

final class Activation {
  static final String PACKAGE = "com.miui.home";

  private boolean attempted;

  static boolean acceptsProcess(String pkg, String process) {
    return PACKAGE.equals(pkg) && PACKAGE.equals(process);
  }

  interface Install {
    void run() throws Exception;
  }

  synchronized boolean activate(
      String pkg, String process, Install install) throws Exception {
    if (!acceptsProcess(pkg, process) || attempted) {
      return false;
    }
    attempted = true; // Even failed preflight is attempted only once per process.
    install.run();
    return true;
  }
}
