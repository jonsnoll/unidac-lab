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

## First-boot core mode

The first controlled boot failed before the Cisco process was
started because the experimental Linux TAP relay failed inside
uBridge.

The runtime is now split into two milestones:

1. process/console/lifecycle core;
2. connected dataplane.

For a core instance with no network bindings the provider uses
the IOL `-N` option to ignore NETMAP and does not start uBridge.

This intentionally isolates first boot from networking so that
process startup, the user-supplied license, console transport and
restart behavior can be validated independently.

Connected IOL dataplane startup is temporarily blocked until its
transport has a bidirectional smoke test.

This ordering also mirrors the separation used by GNS3: IOU is
started and its console is established before IOL networking is
attached.
