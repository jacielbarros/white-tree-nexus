"""Semente de ameaças e vulnerabilidades (Feature 012).

Conteúdo PT-BR **original** inspirado nas categorias típicas da ISO/IEC 27005 (sem reproduzir texto
normativo). Usado por `risk_catalog_service.load_seed()` (idempotente por `code`).
"""

SEED_DESCRIPTION = "Catálogo base de ameaças e vulnerabilidades (ISO 27005, conteúdo original PT-BR)."

# category: human | environmental | technical | organizational
# origin:   deliberate | accidental | environmental | None
THREAT_SEED = [
    {"code": "AME-001", "name": "Acesso não autorizado a sistemas", "category": "human",
     "origin": "deliberate", "description": "Tentativa de obter acesso a sistemas ou dados sem autorização, por terceiros ou pessoas internas."},
    {"code": "AME-002", "name": "Furto ou roubo de equipamentos", "category": "human",
     "origin": "deliberate", "description": "Subtração de notebooks, servidores, mídias ou dispositivos contendo informações da organização."},
    {"code": "AME-003", "name": "Erro de operação ou configuração", "category": "human",
     "origin": "accidental", "description": "Falha humana na operação, configuração ou manutenção de sistemas que compromete a segurança."},
    {"code": "AME-004", "name": "Engenharia social / phishing", "category": "human",
     "origin": "deliberate", "description": "Manipulação de pessoas para obter credenciais, dados sensíveis ou induzir ações indevidas."},
    {"code": "AME-005", "name": "Código malicioso (malware/ransomware)", "category": "technical",
     "origin": "deliberate", "description": "Software malicioso que compromete a confidencialidade, integridade ou disponibilidade dos ativos."},
    {"code": "AME-006", "name": "Indisponibilidade de serviços de TI", "category": "technical",
     "origin": "accidental", "description": "Interrupção de sistemas, redes ou serviços essenciais por falha técnica."},
    {"code": "AME-007", "name": "Vazamento de informações", "category": "human",
     "origin": "deliberate", "description": "Exposição indevida de informações confidenciais a partes não autorizadas."},
    {"code": "AME-008", "name": "Falha de fornecedor ou terceiro", "category": "organizational",
     "origin": "accidental", "description": "Descontinuidade ou má prestação de serviço por fornecedor crítico afetando a operação."},
    {"code": "AME-009", "name": "Falha de energia elétrica", "category": "environmental",
     "origin": "environmental", "description": "Interrupção do fornecimento de energia comprometendo a disponibilidade de ativos."},
    {"code": "AME-010", "name": "Desastre natural (incêndio, alagamento)", "category": "environmental",
     "origin": "environmental", "description": "Eventos ambientais que danificam instalações, equipamentos e informações."},
    {"code": "AME-011", "name": "Alteração não autorizada de dados", "category": "human",
     "origin": "deliberate", "description": "Modificação indevida de informações que compromete a sua integridade."},
    {"code": "AME-012", "name": "Negação de serviço (DoS)", "category": "technical",
     "origin": "deliberate", "description": "Sobrecarga deliberada de sistemas ou redes tornando os serviços indisponíveis."},
    {"code": "AME-013", "name": "Uso indevido de privilégios", "category": "human",
     "origin": "deliberate", "description": "Abuso de permissões legítimas por usuário interno para fins não autorizados."},
    {"code": "AME-014", "name": "Perda de mídia ou backup", "category": "human",
     "origin": "accidental", "description": "Extravio de mídias de armazenamento ou cópias de segurança contendo informações."},
    {"code": "AME-015", "name": "Não conformidade legal ou regulatória", "category": "organizational",
     "origin": "accidental", "description": "Descumprimento de requisitos legais, contratuais ou regulatórios aplicáveis."},
]

# category: technical | physical | organizational | human | process
VULNERABILITY_SEED = [
    {"code": "VUL-001", "name": "Senhas fracas ou compartilhadas", "category": "technical",
     "description": "Uso de senhas fracas, padrão ou compartilhadas que facilitam o acesso não autorizado."},
    {"code": "VUL-002", "name": "Ausência de controle de acesso adequado", "category": "technical",
     "description": "Permissões excessivas ou falta de segregação de funções nos sistemas."},
    {"code": "VUL-003", "name": "Software desatualizado / sem correções", "category": "technical",
     "description": "Sistemas sem aplicação de atualizações e correções de segurança."},
    {"code": "VUL-004", "name": "Falta de cópias de segurança testadas", "category": "process",
     "description": "Backups inexistentes, incompletos ou nunca testados quanto à restauração."},
    {"code": "VUL-005", "name": "Conscientização insuficiente dos colaboradores", "category": "human",
     "description": "Equipe sem treinamento ou conscientização em segurança da informação."},
    {"code": "VUL-006", "name": "Ausência de criptografia de dados sensíveis", "category": "technical",
     "description": "Dados sensíveis armazenados ou transmitidos sem proteção criptográfica."},
    {"code": "VUL-007", "name": "Controle físico de acesso deficiente", "category": "physical",
     "description": "Instalações sem controle adequado de entrada/saída ou de visitantes."},
    {"code": "VUL-008", "name": "Registros e monitoramento insuficientes", "category": "technical",
     "description": "Ausência de logs e monitoramento que permita detectar e investigar incidentes."},
    {"code": "VUL-009", "name": "Gestão de fornecedores frágil", "category": "organizational",
     "description": "Contratos e acordos de nível de serviço sem cláusulas de segurança da informação."},
    {"code": "VUL-010", "name": "Políticas e procedimentos ausentes ou desatualizados", "category": "organizational",
     "description": "Falta de políticas formais ou procedimentos defasados de segurança da informação."},
    {"code": "VUL-011", "name": "Configuração insegura de sistemas", "category": "technical",
     "description": "Sistemas com configurações padrão, serviços desnecessários ou expostos indevidamente."},
    {"code": "VUL-012", "name": "Falta de plano de continuidade", "category": "process",
     "description": "Ausência de planos de continuidade ou recuperação de desastres testados."},
    {"code": "VUL-013", "name": "Descarte inadequado de informações", "category": "process",
     "description": "Descarte de documentos ou mídias sem procedimentos seguros de eliminação."},
    {"code": "VUL-014", "name": "Rede sem segmentação adequada", "category": "technical",
     "description": "Rede plana, sem segmentação, ampliando o alcance de um eventual comprometimento."},
    {"code": "VUL-015", "name": "Dependência de pessoa-chave única", "category": "organizational",
     "description": "Conhecimento ou acesso crítico concentrado em uma única pessoa, sem redundância."},
]
