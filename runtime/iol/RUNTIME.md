# IOL Runtime Contract

## IOL interface model

One IOL Ethernet adapter exposes four interfaces.

The unidac-lab presentation uses sequential port names and maps
them to IOL bay/unit values:

`bay = (port - 1) // 4`

`unit = (port - 1) % 4`

## NETMAP

For an application ID `A`, the local uBridge-side IOL ID is
`A + 512`.

The provider writes 16 bays x 4 units to the NETMAP file.

## Network path

Planned data path for a connected port:

IOL port
-> IOL NETMAP unix transport
-> uBridge iol_bridge
-> UDP pair
-> uBridge generic bridge
-> TAP
-> existing Linux/libvirt bridge

The TAP is created only while the runtime is active and is
removed during shutdown.

## Console

The IOL local console is stdin/stdout.

The daemon wraps that stream with a localhost-only TCP console.

The frontend/AgentD integration will proxy that local console in
the next stage.

## License gate

The runtime requires a user-supplied authorized iourc.

No license generation is implemented.
