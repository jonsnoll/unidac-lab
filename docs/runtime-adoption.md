
# Runtime Adoption

A partir da fundacao da v0.4, o unidac-lab diferencia dois
tipos de runtime libvirt.

## Managed

Runtime criado pelo proprio unidac-lab.

O unidac-lab pode criar, validar, iniciar, parar e remover a
definicao da VM gerenciada. O disco overlay continua protegido
pela politica de runtime.

## Adopted

Runtime libvirt que ja existia antes de entrar no Desired State.

Um runtime adotado:

- preserva o nome original do dominio;
- preserva UUID;
- preserva MAC addresses;
- preserva disco e configuracao;
- pode usar Lifecycle e Console quando explicitamente autorizado;
- nunca e recriado pelo Apply;
- nunca e removido pelo botao Remove Runtime.

## Boundary privilegiada

Dominios fora do namespace `ulab-*` continuam bloqueados por
padrao.

A excecao e uma allowlist root-owned:

`/etc/unidac-lab/adopted-domains.json`

Cada entrada vincula nome e UUID. O Agent valida o UUID real do
libvirt antes de operar um dominio adotado.

O backend nao recebe um comando para incluir novos dominios nessa
allowlist. A inclusao faz parte de uma operacao administrativa
local controlada.

## VXLAN legado

A primeira adocao valida:

- FGT-DC-A;
- FGT-DC-B;
- UNDERLAY;
- LAN-DC-A;
- LAN-DC-B;
- rede `default` como Internet/NAT compartilhada.

O Apply sobre esses recursos e read-only: ele reconhece que o
runtime existe, mas nao recria VM, nao cria overlay e nao altera
as redes adotadas.
