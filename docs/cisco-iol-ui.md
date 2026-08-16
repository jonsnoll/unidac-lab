# Cisco IOL in the unidac-lab UI

Cisco IOL L2 and L3 are available in the device palette.

Supported in this release:

- drag to canvas;
- Desired State;
- Apply Changes prepares the IOL runtime;
- Start;
- Stop;
- Restart;
- Console through the existing WebSocket console UI;
- Remove Runtime while stopped.

The platform does not push IOS configuration. The operator configures the
Cisco device manually through the console.

## Dataplane status

IOL links can be drawn and saved in Desired State, but they are not yet bound
to the IOL process. Apply emits a warning for these links and continues with
the core runtime. The actual Ethernet dataplane is a separate milestone.

## Security boundary

The backend remains non-root. Privileged IOL operations are exposed only as
fixed AgentD commands for managed `ulab-iol-*` instances and fixed Cisco
templates. No license installation or key-generation command is exposed to
the backend.
