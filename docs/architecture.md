# Arquitetura do unidac-lab

## Estados principais

A plataforma trabalha com três conceitos:

### Desired State

Representa o laboratório que o usuário deseja ter.

### Runtime / Observed State

Representa os recursos que realmente existem no QEMU/libvirt.

### Workspace State

Representa posição e layout visual do canvas.

## Frontend

Tecnologias:

- React
- React Flow
- Vite

Responsabilidades:

- editor de topologia;
- catálogo;
- propriedades;
- Apply Plan;
- lifecycle;
- console;
- Packet Capture;
- Netem;
- visualização do estado dos equipamentos.

O frontend não possui acesso privilegiado ao host.

## Backend

Tecnologia:

FastAPI.

Responsabilidades:

- Desired State;
- Apply Plan;
- Image Library;
- reconciliação;
- lifecycle;
- console WebSocket;
- Packet Capture;
- Netem.

O backend roda como usuário não-root.

O backend não recebe:

- /dev/kvm;
- Docker socket;
- libvirt write socket.

A observação do libvirt pode utilizar o socket read-only.

## Host Agent

O `unidac-lab-agent` é responsável pelas operações privilegiadas.

Entre elas:

- criação de redes libvirt;
- preparação de imagens;
- criação de overlays;
- criação de VMs;
- lifecycle;
- remoção de runtime;
- Packet Capture;
- Netem;
- console serial.

O Agent somente gerencia recursos do namespace do unidac-lab.

## AgentD

O `unidac-lab-agentd` roda diretamente no host através do systemd.

Socket:

/run/unidac-lab/agent.sock

A unit utiliza:

RuntimeDirectory=unidac-lab
RuntimeDirectoryPreserve=yes

Isso permite reiniciar o AgentD sem quebrar o bind mount usado
pelo backend.

## Redes

Redes gerenciadas pelo unidac-lab são:

- persistentes;
- configuradas com autostart.

Assim elas retornam automaticamente após reinicialização.

## VMs

As VMs gerenciadas não utilizam autostart na v0.1.0.

Após reinicialização:

- redes voltam;
- VMs permanecem desligadas.

O usuário decide quando ligar os equipamentos.

## Apply

Apply representa reconciliação de configuração.

Para uma VM existente desligada:

Apply não altera seu power state.

O power state é tratado exclusivamente pelo Lifecycle.

## Armazenamento

Imagens base permanecem preservadas.

Cada VM utiliza seu próprio overlay QCOW2.

Atualmente o estado do laboratório fica em:

labs/

Esse diretório não é versionado pelo Git.

Em uma versão futura o runtime poderá ser movido para algo como:

/var/lib/unidac-lab
