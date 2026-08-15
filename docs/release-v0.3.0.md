# unidac-lab v0.3.0

Data da release: 15/08/2026

## Resumo

A v0.3.0 consolida uma rodada de polimento visual e melhoria do
Packet Capture Preview.

A release adiciona identidade visual própria para os principais
tipos de equipamento e aumenta a capacidade de identificação de
tráfego Layer 2 em laboratórios de rede.

## Identidade visual

O catálogo e os nodes planejados/reconciliados do canvas passam
a utilizar ícones SVG próprios por tipo de equipamento.

Tipos contemplados:

- Internet / NAT;
- Network;
- endpoint Linux;
- Windows Coming Soon;
- firewall Fortinet;
- appliance genérico.

Os ícones são componentes próprios do unidac-lab e não dependem
de logos proprietários de fabricantes.

## Packet Capture Preview Layer 2

Além dos protocolos já suportados na v0.2.0, o parser passa a
identificar de forma básica:

- STP / IEEE 802.1D;
- LLDP;
- LACP / Slow Protocols;
- CDP;
- EAPOL / 802.1X;
- IEEE 802.3 / LLC.

Frames ainda não reconhecidos continuam com fallback genérico.

## Teste dedicado do parser

Foi adicionado:

```text
scripts/packet-parser-smoke.sh
```

O smoke fabrica frames Ethernet controlados e valida
automaticamente a identificação de:

- STP;
- LLDP;
- LACP;
- CDP;
- EAPOL.

## Regressão validada

Antes da release foram executados:

- status.sh;
- doctor.sh;
- smoke.sh;
- packet-parser-smoke.sh;
- packet-preview-smoke.sh.

A validação também confirma:

- backend e frontend healthy;
- AgentD ativo;
- libvirt ativo;
- VMs gerenciadas running;
- Git worktree clean;
- main sincronizada com GitHub.

## Arquitetura

A v0.3.0 mantém o mesmo limite de segurança das releases
anteriores:

- frontend sem acesso privilegiado;
- backend não-root;
- backend sem /dev/kvm;
- backend sem Docker socket;
- backend sem libvirt write socket;
- operações privilegiadas isoladas no Host Agent/AgentD.

A leitura do Packet Preview continua sendo feita no backend a
partir do PCAP montado como read-only.

## Limitações atuais

Ainda ficam para versões futuras:

- Packet Preview em tempo real;
- filtros de captura pela interface;
- filtros de exibição;
- árvore completa de protocolos;
- visualização hexadecimal;
- Netem independente por direção;
- autenticação;
- acesso pela rede;
- múltiplos laboratórios;
- instalador;
- runtime Windows;
- appliances gerenciados Cisco, Huawei e Juniper;
- importação/exportação de labs;
- templates de laboratórios.

## Histórico de releases

### v0.1.0

Primeiro MVP funcional.

Commit:

```text
bed76c9056099508104fe2696d38358f3068af13
```

### v0.2.0

Packet Capture Preview.

Commit:

```text
34d3254e83c1d896e8d9ba3c02eeeb65e40ff263
```

### v0.3.0

Identidade visual e reconhecimento Layer 2 no Packet Preview.

O commit final desta release é criado após esta documentação.
