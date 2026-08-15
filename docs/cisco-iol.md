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
