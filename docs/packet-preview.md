# Packet Capture Preview

O Packet Capture Preview permite visualizar um resumo dos
pacotes capturados diretamente na interface do unidac-lab.

## Fluxo

VM / interface
      |
      v
tcpdump
      |
      v
PCAP
      |
      v
Backend
      |
      v
dpkt
      |
      v
JSON
      |
      v
Frontend

A captura continua sendo executada pelo Host Agent.

O preview nao adiciona novas operacoes privilegiadas.

O backend possui acesso somente leitura aos PCAPs gerados pelo
Agent.

## Endpoint

GET /api/lab/captures/{capture_id}/preview

Parametro:

limit

Intervalo permitido:

1 ate 500

Valor padrao:

100

## Informacoes apresentadas

Cada pacote possui:

- numero;
- tempo relativo;
- origem;
- destino;
- protocolo;
- tamanho;
- informacao resumida.

A primeira implementacao possui suporte basico para:

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

Protocolos Layer 2 ainda nao reconhecidos aparecem como frames
Ethernet genericos.

## Interface

Depois de parar uma captura, o preview e carregado
automaticamente.

Continuam disponiveis:

Refresh Preview
Download PCAP

## Limitacoes

Esta implementacao nao pretende substituir o Wireshark.

Ainda nao existem:

- visualizacao em tempo real;
- filtros de captura pela interface;
- filtros de exibicao;
- arvore completa de protocolos;
- hexadecimal do pacote;
- paginacao avancada;
- decodificacao completa de protocolos Layer 2.
