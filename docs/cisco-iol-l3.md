# Cisco IOL L3 Switch

## Estado

O runtime core desta imagem foi validado com:

- ELF32 x86;
- dependencias dinamicas resolvidas;
- boot do processo IOL;
- console serial via TCP localhost;
- lifecycle do provider.

A plataforma nao injeta configuracao Cisco. VLAN, IP, HSRP, OSPF,
routing e demais configuracoes ficam sob controle do usuario no console.

## Imagem

- store: `images/store/cisco/cisco-iol-l3-switch/base.bin`
- SHA256: `dc74c28bfb45e8298ce220aedb21940d1f5e7c5d1967d13da5e339741c9619a9`

## Pendente

O dataplane conectado do provider IOL continua separado do core runtime.
Enquanto essa etapa nao for liberada, o equipamento pode ser criado,
iniciado, parado e acessado via console, mas os links desenhados no canvas
nao sao aplicados ao processo IOL.
