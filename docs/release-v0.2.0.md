# unidac-lab v0.2.0

Data da release: 15/08/2026

## Resumo

A v0.2.0 consolida a primeira evolucao funcional apos o MVP
v0.1.0 e adiciona visualizacao de pacotes capturados diretamente
na interface web.

A release mantem a arquitetura local-only da v0.1.0, com
frontend e backend containerizados e operacoes privilegiadas
isoladas no Host Agent/AgentD.

## Principal novidade

### Packet Capture Preview

O Packet Capture existente agora permite:

- iniciar e parar uma captura pelo Link Tools;
- visualizar os pacotes capturados na propria interface;
- atualizar o preview com Refresh Preview;
- continuar baixando o arquivo PCAP original;
- limitar a leitura da API entre 1 e 500 pacotes;
- usar 100 pacotes como limite padrao da interface.

A tabela apresenta:

- numero;
- tempo relativo;
- origem;
- destino;
- protocolo;
- tamanho;
- informacao resumida.

O parser possui suporte basico para:

- Ethernet;
- ARP;
- IPv4;
- IPv6;
- TCP;
- UDP;
- ICMP;
- ICMPv6;
- DNS;
- DHCP;
- flags TCP.

Frames Layer 2 ainda nao reconhecidos especificamente continuam
sendo apresentados como frames Ethernet genericos.

## Arquitetura

O fluxo do Packet Preview e:

```text
VM / interface
      |
      v
tcpdump via Host Agent
      |
      v
PCAP
      |
      v
Backend read-only
      |
      v
dpkt
      |
      v
JSON
      |
      v
Frontend
```

Nenhuma nova operacao privilegiada foi adicionada ao backend.

## Testes adicionados

A release inclui:

```text
scripts/packet-preview-smoke.sh
```

O teste valida:

- existencia do endpoint no OpenAPI;
- inicio e parada de captura real;
- leitura do preview;
- schema retornado;
- limite de pacotes;
- validacao dos limites 1..500;
- download do PCAP;
- assinatura valida do arquivo PCAP.

## Estado validado antes da release

- plataforma HEALTHY;
- laboratorio RUNNING;
- Doctor: 41 PASS / 0 WARN / 0 FAIL;
- Smoke base: 22 PASS / 0 WARN / 0 SKIP / 0 FAIL;
- Packet Preview Smoke: PASS;
- Git worktree clean;
- main sincronizada com origin/main.

## Limites atuais

A v0.2.0 ainda nao inclui:

- autenticacao;
- acesso remoto nativo;
- Packet Preview em tempo real;
- filtros de captura configuraveis pela interface;
- filtros de exibicao;
- arvore completa de protocolos;
- visualizacao hexadecimal;
- paginacao avancada;
- decodificacao completa de protocolos Layer 2;
- runtime Windows;
- appliances gerenciados Cisco, Huawei e Juniper.

O Windows permanece visivel no catalogo como Coming Soon.

## Compatibilidade com v0.1.0

A tag v0.1.0 permanece imutavel no commit:

```text
bed76c9056099508104fe2696d38358f3068af13
```

A v0.2.0 e uma evolucao da main e nao altera a referencia
historica da primeira release.
