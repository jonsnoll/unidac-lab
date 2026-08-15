# unidac-lab

O `unidac-lab` é uma plataforma local para criação e execução
de laboratórios virtuais de rede.

A ideia é permitir a criação visual de topologias, semelhante ao
conceito de plataformas como EVE-NG e PNETLab, porém utilizando
uma arquitetura própria.

## Versão atual v0.3.0

A `v0.3.0` representa a versão estável atual do projeto. Ela evolui o Packet Capture Preview com identificação básica de protocolos Layer 2 e adiciona identidade visual por tipo de equipamento no catálogo e no canvas.

Esta versão foi desenvolvida e validada no ambiente atual:

- Windows com WSL2;
- Ubuntu;
- QEMU/KVM;
- libvirt;
- Docker Compose;
- React;
- FastAPI.

A interface está disponível localmente em:

http://localhost

Nesta versão ainda não existe autenticação.

## Recursos disponíveis

A versão atual possui:

- editor visual de topologia;
- catálogo de equipamentos;
- ícones visuais por tipo de equipamento;
- FortiGate virtual;
- Linux virtual genérico;
- Internet / NAT;
- rede Layer 2 isolada;
- biblioteca de imagens;
- persistência da topologia;
- persistência do layout;
- Apply Plan;
- Apply Changes;
- Start, Shutdown e Restart de VMs;
- remoção segura de runtime;
- console serial pelo navegador;
- Packet Capture;
- preview dos pacotes capturados na interface;
- identificação básica de STP, LLDP, LACP, CDP, EAPOL e IEEE 802.3/LLC;
- download de PCAP;
- latência em links;
- jitter;
- perda de pacotes;
- limitação de banda;
- Host Agent privilegiado;
- backend não-root;
- frontend/backend em Docker Compose;
- scripts de status, diagnóstico e smoke test.

## Catálogo atual

Disponível:

- Internet / NAT
- Network
- Linux VM
- FortiGate VM

Windows aparece no catálogo como:

Coming Soon

e está desabilitado na versão atual.

## Modelo do laboratório

O unidac-lab separa três estados:

Desired State:
o que o usuário desenhou.

Runtime / Observed State:
o que existe no QEMU/libvirt.

Workspace State:
posição visual dos equipamentos no canvas.

## Apply e Lifecycle

O Apply Changes é responsável por criar e reconciliar a
configuração do laboratório.

O Apply não liga automaticamente uma VM existente que esteja
desligada.

O controle de energia é separado:

- Start
- Shutdown
- Restart

Isso evita que um Apply ligue equipamentos sem intenção do
usuário.

## Comportamento após reinicialização

O comportamento abaixo foi validado:

- Docker volta automaticamente;
- libvirt volta automaticamente;
- AgentD volta automaticamente;
- backend e frontend voltam automaticamente;
- redes gerenciadas voltam ativas;
- VMs permanecem desligadas.

O usuário escolhe quando iniciar as VMs pelo painel.

## Imagens

Imagens proprietárias de fabricantes não fazem parte deste
repositório.

O usuário deve fornecer imagens que esteja autorizado a utilizar.

As imagens base são preservadas e as VMs utilizam overlays QCOW2.

## Scripts operacionais

Status rápido:

./scripts/status.sh

Diagnóstico completo:

./scripts/doctor.sh

Teste funcional:

./scripts/smoke.sh

Exemplo de ambiente saudável com laboratório desligado:

PLATFORM: HEALTHY
LAB     : STOPPED
RESULT  : HEALTHY

Quando as VMs estão ligadas:

PLATFORM: HEALTHY
LAB     : RUNNING
RESULT  : HEALTHY

## Limitações conhecidas da v0.3.0

A versão atual ainda possui algumas limitações:

- acesso somente local;
- sem autenticação;
- apenas um laboratório atual;
- Windows ainda não implementado;
- Cisco ainda não implementado;
- Huawei ainda não implementado;
- Juniper ainda não implementado;
- sem instalador para máquina limpa;
- estado do laboratório ainda armazenado em `labs/`;
- Packet Capture ainda não possui visualização ao vivo;
- Netem ainda não possui controle independente por direção;
- infraestrutura libvirt externa fica escondida do canvas normal.

Esses itens ficam para versões futuras.

## Documentação

Arquitetura:

docs/architecture.md

Roadmap:

docs/roadmap.md

Checklist da release:

docs/release-v0.1.0.md

Release v0.2.0:

docs/release-v0.2.0.md

Release v0.3.0:

docs/release-v0.3.0.md
