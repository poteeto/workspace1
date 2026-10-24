/* Compile the actual production predicate extracted by test-overlay.py. */
#include <assert.h>
#include <stddef.h>
#include <limits.h>
#include <sys/types.h>
typedef struct {int pid, group;} px_ledger;
enum {PX_ENTRY_PID, PX_ENTRY_PGID};
static int px_ledger_has(const px_ledger *ledger, pid_t id, int kind) {
    return id == (kind == PX_ENTRY_PID ? ledger->pid : ledger->group);
}
#include "known-process-probe-test.inc"
int main(void) {
    px_ledger ledger={123,456};
    assert(px_dsha_known_process_probe(&ledger,123,0));
    assert(px_dsha_known_process_probe(&ledger,-123,0));
    assert(px_dsha_known_process_probe(&ledger,456,0));
    assert(px_dsha_known_process_probe(&ledger,-456,0));
    assert(!px_dsha_known_process_probe(&ledger,789,0));
    assert(!px_dsha_known_process_probe(&ledger,-789,0));
    assert(!px_dsha_known_process_probe(NULL,123,0));
    assert(!px_dsha_known_process_probe(&ledger,0,0));
    assert(!px_dsha_known_process_probe(&ledger,-1,0));
    assert(!px_dsha_known_process_probe(&ledger,INT_MIN,0));
    for(int signal=-1;signal<=64;signal++) if(signal!=0) {
        assert(!px_dsha_known_process_probe(&ledger,123,signal));
        assert(!px_dsha_known_process_probe(&ledger,-123,signal));
    }
}
