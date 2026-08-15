# Roadmap do unidac-lab

## Concluído até a v0.3.0

### Interface

- editor visual de topologia;
- catálogo de equipamentos;
- propriedades;
- visualização de estado.

### Runtime

- FortiGate KVM;
- Linux genérico;
- Internet / NAT;
- rede Layer 2;
- Start;
- Shutdown;
- Restart;
- remoção segura.

### Reconciliação

- Desired State;
- Workspace State;
- Apply Plan;
- Apply Engine;
- reconciliação de runtime.

### Ferramentas

- console serial;
- Packet Capture;
- download de PCAP;
- preview de pacotes capturados;
- latência;
- jitter;
- perda de pacotes;
- limitação de banda.

### Arquitetura

- Host Agent;
- AgentD;
- Unix socket;
- backend não-root;
- Docker Compose;
- recuperação de redes após reboot;
- scripts status.sh;
- doctor.sh;
- smoke.sh.

### Evoluções da v0.3.0

- identidade visual por tipo de equipamento;
- ícones próprios no catálogo e no canvas;
- reconhecimento básico de STP, LLDP, LACP, CDP, EAPOL e IEEE 802.3/LLC no Packet Preview;
- smoke test dedicado ao parser de pacotes.

## Próximas evoluções

- captura ao vivo;
- Cisco;
- Huawei;
- Juniper;
- Windows;
- autenticação;
- acesso pela rede;
- múltiplos laboratórios;
- instalador;
- armazenamento em /var/lib/unidac-lab;
- Netem independente por direção;
- importação/exportação de labs;
- templates de laboratórios.

## Futuro

- controle de usuários;
- quotas;
- contabilização de recursos;
- consumo;
- portal estilo cloud;
- gerenciamento de ambientes de clientes.
