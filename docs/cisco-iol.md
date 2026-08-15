# Cisco IOL Runtime

## Estado

A fundacao do runtime Cisco IOL foi iniciada na linha de
desenvolvimento da v0.4.

O primeiro alvo e um switch Layer 2 usando uma imagem
fornecida localmente pelo usuario.

## Imagem

Template:

`cisco-iol-l2-switch`

Imagem local inicial:

`cisco-iol-l2-adventerprise-15-1-20140814`

Formato detectado:

- ELF 32-bit;
- Intel i386;
- executavel Linux;
- nao e QCOW2;
- nao e uma VM libvirt.

Por isso o provider sera `iol`, separado do provider
`libvirt`.

## Dependencia legada

A imagem analisada requer `libcrypto.so.4`.

Essa biblioteca nao faz parte do userspace moderno padrao do
Ubuntu 24.04.

O projeto nao deve instalar bibliotecas OpenSSL antigas de fonte
nao confiavel diretamente no host.

O provider IOL devera executar em um userspace legado isolado,
mantendo o host WSL moderno e reduzindo o impacto de
dependencias antigas.

## Seguranca e distribuicao

O unidac-lab nao distribui imagens Cisco.

O arquivo binario permanece no image store ignorado pelo Git.
Somente metadata, catalogo e codigo do runtime podem ser
versionados.

O projeto nao gera nem contorna licencas do IOL.

## Sandbox de compatibilidade

O userspace legado passou a ser preparado em uma imagem Docker
isolada.

A imagem Cisco nao e incorporada ao container. O binario e
montado read-only apenas durante validacoes ou execucao futura.

O sandbox usa uma base Linux i386 e recebe somente o pacote
`libssl1.0.0` legado necessario para resolver a dependencia
`libcrypto.so.4`. O pacote e obtido do archive oficial do Ubuntu
e existe somente dentro da imagem do sandbox.

Nao usamos `apt update` da release Trusty. O host Ubuntu 24.04
continua sem a biblioteca legada.

O sandbox roda sem rede, sem capabilities Linux adicionais e com
`no-new-privileges` durante o smoke de compatibilidade.

Nesta etapa somente loader e `ldd` sao executados contra a imagem
Cisco. O IOS nao e iniciado.

## Fases

1. Host readiness i386.
2. Catalogo e metadata.
3. Userspace IOL isolado.
4. Provider IOL.
5. Lifecycle.
6. Console.
7. Network attachment.
8. Packet Capture.
9. Integracao completa com Desired/Observed State.

O template permanece desabilitado no catalogo ate o provider
IOL conseguir criar e conectar uma instancia de forma segura.

## Provider foundation

O provider IOL agora possui um controlador local:

`/usr/local/libexec/unidac-lab-iolctl`

A primeira versao oferece:

- `doctor`;
- `license-status`;
- `prepare`;
- `list`;
- `inspect`;
- `remove-prepared`.

`prepare` nao executa IOS. Ele valida o binario, valida o sandbox
e cria somente um manifesto de estado para a futura instancia.

O estado persistente fica em:

`/var/lib/unidac-lab/iol/instances`

## License gate

O caminho reservado para uma licenca IOL autorizada pelo usuario
e:

`/etc/unidac-lab/iol/iourc`

O unidac-lab nao cria esse arquivo, nao gera chave e nao altera
seu conteudo.

Quando fornecido, o arquivo deve ser:

- propriedade de `root`;
- permissao `0600` ou mais restritiva;
- nao vazio.

Mesmo com uma licenca presente, o comando de startup continua
bloqueado nesta etapa. O proximo marco implementara networking,
console e o contrato de execucao antes de liberar lifecycle.

## Static runtime probe

Antes de implementar o comando de startup, o unidac-lab possui
um probe estatico para analisar o executavel IOL sem inicia-lo.

O probe usa somente:

- `file`;
- `readelf`;
- `strings`;
- SHA256.

Ele procura pistas de:

- opcoes de linha de comando;
- NETMAP/networking;
- interfaces;
- console;
- sockets/UDP;
- variaveis de ambiente;
- referencias de licenciamento.

O probe nao le o conteudo de `iourc` e nao executa o IOS.

A finalidade e evitar implementar o provider com flags
adivinhadas.

## Deep static probe

O primeiro static probe confirmou os principais contratos
visiveis no binario:

- `Usage: <image> [options] <application id>`;
- `NETMAP`;
- `IOURC`;
- `-L` para console remoto;
- `-N` para ignorar NETMAP;
- `-R` para ignorar opcoes do IOURC;
- `-n` para NVRAM;
- `-s` para interfaces seriais.

Antes de implementar startup/networking, o deep static probe
analisa a proximidade fisica dessas strings dentro do ELF.

Isso permite recuperar a tabela de opcoes e pistas de NETMAP
sem executar o IOS e sem adivinhar flags.

## Runtime plumbing

O deep static probe confirmou o contrato de linha de comando do
IOL L2 analisado.

O provider passa a usar o mesmo modelo estrutural comprovado pelo
ecossistema open-source do GNS3:

- application ID unico;
- `-e` em grupos de quatro portas Ethernet;
- `-s 0` para o switch L2 sem interfaces seriais;
- NETMAP local;
- uBridge `iol_bridge`;
- stdin/stdout como console.

Para 8 portas do unidac-lab:

- `port1` = bay 0 / unit 0;
- `port2` = bay 0 / unit 1;
- `port3` = bay 0 / unit 2;
- `port4` = bay 0 / unit 3;
- `port5` = bay 1 / unit 0;
- `port6` = bay 1 / unit 1;
- `port7` = bay 1 / unit 2;
- `port8` = bay 1 / unit 3.

## Private compatibility library

O container de compatibilidade continua existindo como smoke
isolado.

Para o runtime real, `libcrypto.so.4` nao e instalada
globalmente. A biblioteca fica em:

`/opt/unidac-lab/iol-compat/lib`

O processo IOL recebe esse caminho somente por
`LD_LIBRARY_PATH`.

Isso permite executar o IOL no namespace Linux do host, que e
necessario para o NETMAP/uBridge, sem contaminar as bibliotecas
globais do Ubuntu 24.04.

## uBridge

O unidac-lab usa uBridge para adaptar as portas NETMAP do IOL a
NIO UDP e, futuramente, aos bridges Linux do laboratorio.

O commit instalado e registrado em:

`runtime/iol/ubridge.lock.json`

## Lifecycle contract

O provider agora possui o contrato:

- `prepare`;
- `start-plan`;
- `status`;
- `start`;
- `stop`;
- `list`;
- `inspect`;
- `remove-prepared`;
- `ubridge-self-test`.

O comando `start` existe, mas permanece protegido pelo license
gate.

Sem um `iourc` autorizado em `/etc/unidac-lab/iol/iourc`, o
provider recusa iniciar o processo Cisco.

O unidac-lab nao gera chaves, nao altera uma chave e nao tenta
contornar a verificacao do executavel.
