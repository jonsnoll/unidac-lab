# unidac-lab Architecture

## Core model

The platform separates three concepts:

- Desired State: what the user designed.
- Runtime State: what exists in QEMU/libvirt.
- Workspace State: visual position and layout.

## Components

### Frontend

React + React Flow.

Responsibilities:

- topology editor
- device properties
- Apply Plan preview
- lifecycle controls
- serial console
- packet capture UI
- runtime state visualization

The frontend never receives privileged host access.

### Backend

FastAPI.

Responsibilities:

- Desired State
- Apply Plan
- Image Library
- reconciliation
- lifecycle APIs
- WebSocket console transport
- packet capture orchestration

The backend must not run as root.

### Host Agent

unidac-lab-agent.

This is the privileged boundary.

Responsibilities include:

- libvirt network creation
- runtime image preparation
- QCOW2 overlays
- VM creation and validation
- VM lifecycle
- runtime removal
- packet capture
- future tc/netem operations

The agent only accepts resources inside the
managed unidac-lab namespace.

### Host runtime

Native Linux host:

- QEMU/KVM
- libvirt
- Linux bridges/tap/vnet
- tcpdump
- tc/netem
- runtime images

## Storage model

Base images are read-only.

Each VM gets its own QCOW2 overlay.

Removing a runtime VM does not delete its
overlay by default.

## Security principles

- Backend does not run as root.
- Browser never sends arbitrary host interface
  names to privileged operations.
- Managed VM names use the ulab- namespace.
- Agent must not control external VMs.
- Runtime image IDs and capture IDs are
  validated before host operations.

## Host Agent transport

The privileged Agent is exposed to the backend
through a local Unix socket:

`/run/unidac-lab/agent.sock`

`unidac-lab-agentd` runs natively on the host
under systemd.

Privileged operations go through agentd:

- VM creation
- lifecycle
- runtime removal
- image/overlay preparation
- network creation
- packet capture
- netem
- serial console

For the MVP, libvirt observation may remain
read-only in the backend through the libvirt
read-only socket.

No libvirt write socket is exposed to the
backend container.
