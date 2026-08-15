# Checklist - unidac-lab v0.1.0

## Plataforma

- [x] Docker ativo
- [x] libvirt ativo
- [x] AgentD ativo
- [x] backend saudável
- [x] frontend saudável
- [x] Agent API saudável

## Runtime

- [x] FortiGate funcionando
- [x] Linux funcionando
- [x] Network funcionando
- [x] Internet / NAT funcionando
- [x] Start funcionando
- [x] Shutdown funcionando
- [x] Restart funcionando

## Apply

- [x] Apply Plan funcionando
- [x] Apply com zero erros
- [x] Apply preserva VM desligada
- [x] rede gerenciada recebe autostart

## Ferramentas

- [x] console serial
- [x] Packet Capture
- [x] download PCAP
- [x] latência
- [x] jitter
- [x] perda de pacotes
- [x] limitação de banda

## Segurança

- [x] backend não-root
- [x] backend sem /dev/kvm
- [x] backend sem Docker socket
- [x] backend sem libvirt write socket
- [x] operações privilegiadas através do Agent

## Recuperação

- [x] WSL shutdown testado
- [x] Docker volta automaticamente
- [x] libvirt volta automaticamente
- [x] AgentD volta automaticamente
- [x] backend/frontend voltam
- [x] Network volta ACTIVE
- [x] Network permanece Autostart=yes
- [x] VMs permanecem SHUTOFF
- [x] VMs podem ser ligadas pela interface
- [x] smoke final passa após Start

## Smoke final esperado

./scripts/smoke.sh

Resultado esperado:

PASS
WARN: 0
SKIP: 0
FAIL: 0

## Antes da tag

- [ ] documentação commitada
- [ ] Git limpo
- [ ] doctor.sh sem FAIL
- [ ] smoke.sh sem FAIL
- [ ] criar tag v0.1.0
