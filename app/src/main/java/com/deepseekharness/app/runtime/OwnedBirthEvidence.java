package com.deepseekharness.app.runtime;

import com.deepseekharness.app.util.ProcessIdentity;

/** Current pre-guest signed birth only; never used to claim an old PID or release an exit barrier. */
final class OwnedBirthEvidence {
  static ProcessIdentity current(
      ProcessIdentity born, ProcessIdentity inspected, boolean rawAlive, int sid) {
    if (born == null || !rawAlive || !born.ownsSession() || born.exited()) return null;
    if (inspected != null)
      return born.sameProcess(inspected) && inspected.ownsSession() && !inspected.exited()
          ? inspected
          : null;
    return sid == born.session ? born : null;
  }

  /**
   * Android may deny the parent access to its already-running child's /proc stat
   * and getsid() with EPERM/EACCES even though the child can read /proc/self/stat.
   * A matching kernel SO_PEERCRED on our nonce-protected native control socket
   * is an independent recheck, but ONLY in that exact permission-denied case.
   *
   * Never waive a readable-but-mismatched stat, exited process, ESRCH, or a
   * positive SID belonging to a different session.
   */
  static boolean canUseKernelPeerRecheck(
      ProcessIdentity born, boolean procReadDenied, int kernelSid,
      boolean rawAlive) {
    return born != null
        && born.ownsSession()
        && !born.exited()
        && procReadDenied
        && rawAlive
        && (kernelSid == -1 /* EPERM */ || kernelSid == -13 /* EACCES */);
  }

  static boolean peer(ProcessIdentity born, int pid, int uid, int appUid, boolean rawAlive) {
    return born != null
        && rawAlive
        && born.ownsSession()
        && !born.exited()
        && born.pid == pid
        && uid == appUid;
  }

  private OwnedBirthEvidence() {}
}
