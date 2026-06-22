"""Seed da ISO/IEC 27001:2022 — Cláusulas 4–10 e 93 controles do Anexo A.

Versão: 2022.1
Carregado de forma idempotente pela migration e por `gap_seed_service.load_seed()`.
Estrutura: lista de dicts prontos para inserção em `gap_seed_item`.
"""

from wtnapp.settings import GapDimension, GapTheme

SEED_VERSION = "2022.1"
SEED_DESCRIPTION = "ISO/IEC 27001:2022 — Cláusulas 4–10 e Anexo A (93 controles)"

# ---------------------------------------------------------------------------
# Cláusulas 4–10 (dimension=clause, theme=None)
# ---------------------------------------------------------------------------

CLAUSES = [
    {
        "ref_code": "4",
        "name": "Contexto da organização",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Compreender a organização, seu contexto interno e externo, as partes interessadas "
            "relevantes e seus requisitos, e definir o escopo do SGSI."
        ),
        "order": 1,
    },
    {
        "ref_code": "5",
        "name": "Liderança",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Demonstrar comprometimento da alta direção, estabelecer política de segurança da "
            "informação e definir papéis, responsabilidades e autoridades organizacionais."
        ),
        "order": 2,
    },
    {
        "ref_code": "6",
        "name": "Planejamento",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Tratar riscos e oportunidades, definir objetivos de segurança da informação e "
            "planejar as mudanças necessárias no SGSI."
        ),
        "order": 3,
    },
    {
        "ref_code": "7",
        "name": "Apoio",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Prover recursos, competências, conscientização, comunicação e informação "
            "documentada necessários para o SGSI."
        ),
        "order": 4,
    },
    {
        "ref_code": "8",
        "name": "Operação",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Planejar, implementar e controlar os processos do SGSI, incluindo avaliação e "
            "tratamento de riscos de segurança da informação."
        ),
        "order": 5,
    },
    {
        "ref_code": "9",
        "name": "Avaliação de desempenho",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Monitorar, medir, analisar e avaliar o SGSI, conduzir auditorias internas e "
            "realizar revisão pela direção."
        ),
        "order": 6,
    },
    {
        "ref_code": "10",
        "name": "Melhoria",
        "dimension": GapDimension.clause,
        "theme": None,
        "objective": (
            "Tratar não conformidades e ações corretivas, e melhorar continuamente a "
            "adequação, suficiência e eficácia do SGSI."
        ),
        "order": 7,
    },
]

# ---------------------------------------------------------------------------
# Anexo A — Controles organizacionais (A.5, 37 controles)
# ---------------------------------------------------------------------------

A5_CONTROLS = [
    ("A.5.1", "Políticas de segurança da informação", "Definir, aprovar pela direção, publicar e comunicar políticas de segurança da informação e revisá-las em intervalos planejados ou quando ocorrerem mudanças significativas.", 1),
    ("A.5.2", "Papéis e responsabilidades de segurança da informação", "Definir e atribuir responsabilidades de segurança da informação.", 2),
    ("A.5.3", "Segregação de funções", "Segregar funções conflitantes para reduzir riscos de acesso não autorizado, modificação ou uso indevido de ativos.", 3),
    ("A.5.4", "Responsabilidades da direção", "Exigir que a direção demonstre comprometimento com a segurança da informação.", 4),
    ("A.5.5", "Contato com autoridades", "Manter contatos apropriados com as autoridades relevantes.", 5),
    ("A.5.6", "Contato com grupos de interesse especial", "Manter contatos com grupos de interesse especial e fóruns especializados em segurança da informação.", 6),
    ("A.5.7", "Inteligência de ameaças", "Coletar e analisar informações sobre ameaças de segurança da informação para produzir inteligência de ameaças.", 7),
    ("A.5.8", "Segurança da informação no gerenciamento de projetos", "Integrar segurança da informação ao gerenciamento de projetos.", 8),
    ("A.5.9", "Inventário de informações e outros ativos associados", "Identificar e manter inventário de informações e outros ativos associados, incluindo proprietários.", 9),
    ("A.5.10", "Uso aceitável de informações e outros ativos associados", "Identificar, documentar e implementar regras de uso aceitável e procedimentos para informações e ativos.", 10),
    ("A.5.11", "Devolução de ativos", "Assegurar devolução de ativos da organização por funcionários e outras partes ao término do contrato.", 11),
    ("A.5.12", "Classificação da informação", "Classificar informações de acordo com as necessidades de segurança da informação baseado na confidencialidade, integridade e disponibilidade.", 12),
    ("A.5.13", "Rotulagem de informações", "Desenvolver e implementar conjunto de procedimentos para rotulagem de informações de acordo com o esquema de classificação.", 13),
    ("A.5.14", "Transferência de informações", "Implementar regras, procedimentos ou acordos para transferência de informações para todas as partes.", 14),
    ("A.5.15", "Controle de acesso", "Estabelecer e implementar regras para controlar acesso físico e lógico a informações e outros ativos associados.", 15),
    ("A.5.16", "Gerenciamento de identidades", "Gerenciar o ciclo de vida completo das identidades.", 16),
    ("A.5.17", "Informações de autenticação", "Controlar alocação e gerenciamento de informações de autenticação conforme processo de gerenciamento.", 17),
    ("A.5.18", "Direitos de acesso", "Provisionar, revisar, modificar e remover direitos de acesso a informações e outros ativos associados.", 18),
    ("A.5.19", "Segurança da informação nas relações com fornecedores", "Identificar e implementar processos e procedimentos para gerenciar riscos de segurança da informação associados ao uso de produtos ou serviços de fornecedores.", 19),
    ("A.5.20", "Tratamento da segurança da informação nos acordos com fornecedores", "Estabelecer e acordar requisitos de segurança da informação relevantes com cada fornecedor.", 20),
    ("A.5.21", "Gerenciamento da segurança da informação na cadeia de suprimentos de TIC", "Definir e implementar processos e procedimentos para gerenciar riscos de segurança da informação associados ao uso de produtos e serviços de TIC.", 21),
    ("A.5.22", "Monitoramento, revisão e gerenciamento de mudanças dos serviços de fornecedores", "Monitorar, revisar, avaliar e gerenciar mudanças nas práticas de segurança da informação dos fornecedores regularmente.", 22),
    ("A.5.23", "Segurança da informação para o uso de serviços em nuvem", "Estabelecer processos para aquisição, uso, gerenciamento e saída de serviços em nuvem de acordo com os requisitos de segurança da informação.", 23),
    ("A.5.24", "Planejamento e preparação do gerenciamento de incidentes de segurança da informação", "Planejar e se preparar para gerenciar incidentes de segurança da informação definindo, estabelecendo e comunicando processos, papéis e responsabilidades.", 24),
    ("A.5.25", "Avaliação e decisão sobre eventos de segurança da informação", "Avaliar eventos de segurança da informação e decidir se eles devem ser categorizados como incidentes.", 25),
    ("A.5.26", "Resposta a incidentes de segurança da informação", "Responder a incidentes de segurança da informação de acordo com os procedimentos documentados.", 26),
    ("A.5.27", "Aprendizado com incidentes de segurança da informação", "Usar o conhecimento obtido de incidentes para fortalecer e melhorar os controles de segurança.", 27),
    ("A.5.28", "Coleta de evidências", "Estabelecer e implementar procedimentos para identificação, coleta, aquisição e preservação de evidências.", 28),
    ("A.5.29", "Segurança da informação durante a disrupção", "Planejar como manter a segurança da informação em nível apropriado durante a disrupção.", 29),
    ("A.5.30", "Prontidão de TIC para continuidade dos negócios", "Planejar, implementar, manter e testar a prontidão de TIC para continuidade dos negócios.", 30),
    ("A.5.31", "Requisitos legais, estatutários, regulatórios e contratuais", "Identificar, documentar e manter atualizados os requisitos legais, estatutários, regulatórios e contratuais relevantes.", 31),
    ("A.5.32", "Direitos de propriedade intelectual", "Implementar procedimentos apropriados para proteger direitos de propriedade intelectual.", 32),
    ("A.5.33", "Proteção de registros", "Proteger registros contra perda, destruição, falsificação, acesso não autorizado e liberação não autorizada.", 33),
    ("A.5.34", "Privacidade e proteção de informações de identificação pessoal (PII)", "Identificar e atender os requisitos de privacidade e proteção de PII de acordo com legislação e regulamentações aplicáveis.", 34),
    ("A.5.35", "Revisão independente da segurança da informação", "Revisar a abordagem da organização para gerenciar e implementar a segurança da informação em intervalos planejados ou quando mudanças significativas ocorrerem.", 35),
    ("A.5.36", "Conformidade com políticas, regras e normas de segurança da informação", "Revisar regularmente a conformidade do processamento e procedimentos de informação com as políticas, regras e normas de segurança da informação.", 36),
    ("A.5.37", "Procedimentos operacionais documentados", "Documentar, manter e disponibilizar procedimentos operacionais a todos que precisem deles.", 37),
]

# ---------------------------------------------------------------------------
# Anexo A — Controles de pessoas (A.6, 8 controles)
# ---------------------------------------------------------------------------

A6_CONTROLS = [
    ("A.6.1", "Triagem", "Verificar e revisar antecedentes de todos os candidatos a tornarem-se colaboradores, conforme leis, regulamentações e ética aplicáveis.", 1),
    ("A.6.2", "Termos e condições de emprego", "Os acordos contratuais com funcionários e prestadores de serviço devem declarar as responsabilidades deles e da organização para segurança da informação.", 2),
    ("A.6.3", "Conscientização, educação e treinamento em segurança da informação", "Funcionários e partes interessadas relevantes devem receber conscientização, educação e treinamento adequados em segurança da informação.", 3),
    ("A.6.4", "Processo disciplinar", "Formalizar e comunicar o processo disciplinar para tomar ações contra funcionários e outras partes que cometeram violações da política de segurança da informação.", 4),
    ("A.6.5", "Responsabilidades após encerramento ou mudança de emprego", "Definir, monitorar e comunicar as responsabilidades de segurança da informação que permanecem válidas após encerramento ou mudança de emprego.", 5),
    ("A.6.6", "Acordos de confidencialidade ou não divulgação", "Identificar, documentar, revisar regularmente e assinar os acordos de confidencialidade ou não divulgação refletindo as necessidades de proteção da informação.", 6),
    ("A.6.7", "Trabalho remoto", "Implementar medidas de segurança quando funcionários trabalham remotamente para proteger as informações acessadas, processadas ou armazenadas fora das instalações da organização.", 7),
    ("A.6.8", "Relato de eventos de segurança da informação", "Fornecer mecanismo para que funcionários e prestadores de serviço reportem eventos de segurança da informação observados ou suspeitos por canais apropriados e em tempo hábil.", 8),
]

# ---------------------------------------------------------------------------
# Anexo A — Controles físicos (A.7, 14 controles)
# ---------------------------------------------------------------------------

A7_CONTROLS = [
    ("A.7.1", "Perímetros de segurança física", "Definir e usar perímetros de segurança para proteger áreas que contenham informações e outros ativos associados.", 1),
    ("A.7.2", "Entrada física", "As áreas seguras devem ser protegidas por controles de entrada adequados e pontos de acesso.", 2),
    ("A.7.3", "Segurança de escritórios, salas e instalações", "Projetar e implementar segurança física para escritórios, salas e instalações.", 3),
    ("A.7.4", "Monitoramento de segurança física", "Monitorar continuamente as instalações para detectar acessos físicos não autorizados.", 4),
    ("A.7.5", "Proteção contra ameaças físicas e ambientais", "Projetar e implementar proteção contra ameaças físicas e ambientais como desastres naturais e outros perigos físicos intencionais ou não intencionais.", 5),
    ("A.7.6", "Trabalho em áreas seguras", "Projetar e implementar medidas de segurança para trabalho em áreas seguras.", 6),
    ("A.7.7", "Mesa limpa e tela limpa", "Definir e implementar política de mesa limpa para documentos e mídias de armazenamento removíveis e política de tela limpa para instalações de processamento de informação.", 7),
    ("A.7.8", "Localização e proteção de equipamentos", "Posicionar e proteger equipamentos com segurança para reduzir riscos de ameaças físicas e ambientais e oportunidades de acesso não autorizado.", 8),
    ("A.7.9", "Segurança de ativos fora das instalações", "Proteger ativos fora das instalações.", 9),
    ("A.7.10", "Mídia de armazenamento", "Gerenciar mídias de armazenamento ao longo de seu ciclo de vida de aquisição, uso, transporte e descarte de acordo com o esquema de classificação e requisitos de manuseio.", 10),
    ("A.7.11", "Utilidades de suporte", "Proteger instalações de processamento de informação contra falhas de energia e outras interrupções causadas por falhas em utilidades de suporte.", 11),
    ("A.7.12", "Segurança do cabeamento", "Proteger cabos que carregam energia, dados ou serviços de informação de suporte contra interceptação, interferência ou danos.", 12),
    ("A.7.13", "Manutenção de equipamentos", "Manter equipamentos corretamente para garantir disponibilidade, integridade e confidencialidade das informações.", 13),
    ("A.7.14", "Descarte ou reutilização segura de equipamentos", "Verificar itens de equipamento que contenham mídias de armazenamento para garantir que dados sensíveis e software licenciado foram removidos ou sobrescritos com segurança antes do descarte ou reutilização.", 14),
]

# ---------------------------------------------------------------------------
# Anexo A — Controles tecnológicos (A.8, 34 controles)
# ---------------------------------------------------------------------------

A8_CONTROLS = [
    ("A.8.1", "Dispositivos de endpoint do usuário", "Proteger informações armazenadas, processadas ou acessíveis por dispositivos de endpoint do usuário.", 1),
    ("A.8.2", "Direitos de acesso privilegiado", "Restringir e gerenciar direitos de acesso privilegiado.", 2),
    ("A.8.3", "Restrição de acesso à informação", "Restringir acesso a informações e outros ativos associados de acordo com a política de controle de acesso estabelecida.", 3),
    ("A.8.4", "Acesso ao código-fonte", "Gerenciar acesso de leitura e escrita ao código-fonte, ferramentas de desenvolvimento e bibliotecas de software de forma adequada.", 4),
    ("A.8.5", "Autenticação segura", "Implementar tecnologias e procedimentos de autenticação segura com base em restrições de acesso a informações e políticas de controle de acesso.", 5),
    ("A.8.6", "Gerenciamento de capacidade", "Monitorar e ajustar o uso de recursos, e fazer projeções de necessidades futuras de capacidade para garantir o desempenho requerido.", 6),
    ("A.8.7", "Proteção contra malware", "Implementar proteção contra malware e suportar isso com conscientização apropriada de usuários.", 7),
    ("A.8.8", "Gerenciamento de vulnerabilidades técnicas", "Obter informações sobre vulnerabilidades técnicas dos sistemas de informação em uso, avaliar a exposição da organização e tomar medidas apropriadas.", 8),
    ("A.8.9", "Gerenciamento de configuração", "Estabelecer, documentar, implementar, monitorar e revisar configurações, incluindo configurações de segurança, para hardware, software, serviços e redes.", 9),
    ("A.8.10", "Exclusão de informações", "Excluir informações armazenadas em sistemas de informação, dispositivos ou em qualquer outra mídia de armazenamento quando não mais necessárias.", 10),
    ("A.8.11", "Mascaramento de dados", "Usar mascaramento de dados de acordo com a política de controle de acesso da organização e outros requisitos relacionados.", 11),
    ("A.8.12", "Prevenção de vazamento de dados", "Aplicar medidas de prevenção de vazamento de dados a sistemas, redes e outros dispositivos que processem, armazenem ou transmitam informações sensíveis.", 12),
    ("A.8.13", "Backup de informações", "Manter e testar regularmente cópias de backup de informações, software e sistemas.", 13),
    ("A.8.14", "Redundância de instalações de processamento de informação", "Implementar instalações de processamento de informação com redundância suficiente para atender aos requisitos de disponibilidade.", 14),
    ("A.8.15", "Log", "Produzir, armazenar, proteger e analisar logs que registrem atividades, exceções, falhas e outros eventos relevantes.", 15),
    ("A.8.16", "Atividades de monitoramento", "Monitorar redes, sistemas e aplicações para comportamento anormal e tomar ações apropriadas para avaliar possíveis incidentes de segurança da informação.", 16),
    ("A.8.17", "Sincronização de relógio", "Os relógios dos sistemas de processamento de informação usados pela organização devem ser sincronizados com fontes de tempo aprovadas.", 17),
    ("A.8.18", "Uso de programas utilitários privilegiados", "Restringir e monitorar rigorosamente o uso de programas utilitários com capacidade de substituir controles de sistema e aplicação.", 18),
    ("A.8.19", "Instalação de software em sistemas operacionais", "Implementar procedimentos e medidas para gerenciar com segurança a instalação de software em sistemas operacionais.", 19),
    ("A.8.20", "Segurança de redes", "Proteger redes e seus componentes, conexões e serviços contra ameaças à segurança da informação.", 20),
    ("A.8.21", "Segurança dos serviços de rede", "Identificar, implementar e monitorar mecanismos de segurança, níveis de serviço e requisitos de serviços de rede.", 21),
    ("A.8.22", "Segregação de redes", "Segregar grupos de serviços de informação, usuários e sistemas de informação em redes.", 22),
    ("A.8.23", "Filtragem web", "Gerenciar o acesso a sites externos para reduzir a exposição a conteúdo malicioso.", 23),
    ("A.8.24", "Uso de criptografia", "Definir e implementar regras para uso eficaz de criptografia, incluindo gerenciamento de chaves criptográficas.", 24),
    ("A.8.25", "Ciclo de vida de desenvolvimento seguro", "Estabelecer e aplicar regras para o desenvolvimento seguro de software e sistemas.", 25),
    ("A.8.26", "Requisitos de segurança de aplicações", "Identificar, especificar e aprovar requisitos de segurança da informação ao desenvolver ou adquirir aplicações.", 26),
    ("A.8.27", "Princípios de arquitetura e engenharia de sistemas seguros", "Estabelecer, documentar, manter e aplicar princípios para engenharia de sistemas seguros em quaisquer atividades de desenvolvimento de sistemas de informação.", 27),
    ("A.8.28", "Codificação segura", "Aplicar princípios de codificação segura no desenvolvimento de software.", 28),
    ("A.8.29", "Testes de segurança em desenvolvimento e aceitação", "Definir e implementar processos de teste de segurança no ciclo de vida de desenvolvimento.", 29),
    ("A.8.30", "Desenvolvimento terceirizado", "Dirigir, monitorar e revisar as atividades relacionadas ao desenvolvimento de sistemas terceirizados.", 30),
    ("A.8.31", "Separação dos ambientes de desenvolvimento, teste e produção", "Separar e proteger ambientes de desenvolvimento, teste e produção.", 31),
    ("A.8.32", "Gerenciamento de mudanças", "Sujeitar mudanças em instalações de processamento de informação e sistemas de informação a procedimentos de gerenciamento de mudanças.", 32),
    ("A.8.33", "Informações de teste", "Selecionar, proteger e gerenciar adequadamente as informações de teste.", 33),
    ("A.8.34", "Proteção de sistemas de informação durante testes de auditoria", "Planejar e concordar com testes de auditoria e outras atividades de garantia que envolvam avaliação de sistemas operacionais.", 34),
]


# ---------------------------------------------------------------------------
# Orientação de avaliação por item (Feature 007) — PT-BR ORIGINAL.
# IMPORTANTE: textos próprios; NÃO reproduzir o texto normativo da ISO/IEC 27001/27002.
# `referencia` é derivada do código; aqui ficam apenas `como_avaliar` e `evidencias_esperadas`
# (+ `nota` opcional). Itens sem entrada herdam listas vazias (orientação a curar depois).
# ---------------------------------------------------------------------------

GUIDANCE: dict[str, dict] = {
    # ---- Cláusulas 4–10 ----
    "4": {
        "como_avaliar": [
            "Há um documento que descreve o contexto interno e externo da organização?",
            "As questões relevantes para o SGSI são revisadas periodicamente?",
            "As partes interessadas e seus requisitos estão mapeados e o escopo do SGSI definido?",
        ],
        "evidencias_esperadas": [
            "Documento de análise de contexto (fatores internos/externos)",
            "Mapa de partes interessadas e requisitos",
            "Declaração de escopo do SGSI aprovada",
        ],
    },
    "5": {
        "como_avaliar": [
            "A alta direção demonstra comprometimento formal com o SGSI?",
            "Existe política de segurança da informação aprovada e comunicada?",
            "Papéis, responsabilidades e autoridades de SI estão definidos e atribuídos?",
        ],
        "evidencias_esperadas": [
            "Política de segurança da informação aprovada",
            "Ata/registro de comprometimento da direção",
            "Matriz de papéis e responsabilidades (ex.: RACI)",
        ],
    },
    "6": {
        "como_avaliar": [
            "Há metodologia documentada de avaliação e tratamento de riscos?",
            "Os objetivos de segurança da informação são mensuráveis e têm responsáveis/prazos?",
            "Mudanças no SGSI são planejadas de forma controlada?",
        ],
        "evidencias_esperadas": [
            "Metodologia de gestão de riscos e critérios de aceitação",
            "Plano de tratamento de riscos",
            "Objetivos de SI com métricas, metas e prazos",
        ],
    },
    "7": {
        "como_avaliar": [
            "Os recursos necessários ao SGSI estão providos?",
            "Há programa de competência, conscientização e treinamento?",
            "A informação documentada é controlada (versão, aprovação, distribuição)?",
        ],
        "evidencias_esperadas": [
            "Plano/registros de treinamento e conscientização",
            "Matriz de competências",
            "Procedimento de controle de documentos e registros",
        ],
    },
    "8": {
        "como_avaliar": [
            "Os processos operacionais do SGSI são planejados e controlados?",
            "A avaliação de riscos é executada e mantida atualizada?",
            "O tratamento de riscos é implementado conforme o plano?",
        ],
        "evidencias_esperadas": [
            "Resultado da avaliação de riscos",
            "Registros de execução do plano de tratamento",
            "Procedimentos operacionais documentados",
        ],
    },
    "9": {
        "como_avaliar": [
            "Há indicadores e medição do desempenho do SGSI?",
            "Auditorias internas são planejadas e executadas com independência?",
            "A direção realiza análise crítica do SGSI em intervalos planejados?",
        ],
        "evidencias_esperadas": [
            "Programa e relatórios de auditoria interna",
            "Atas de análise crítica pela direção",
            "Painel de indicadores/métricas de SI",
        ],
    },
    "10": {
        "como_avaliar": [
            "Não conformidades são registradas e tratadas com ações corretivas?",
            "A eficácia das ações corretivas é verificada?",
            "Há evidência de melhoria contínua do SGSI?",
        ],
        "evidencias_esperadas": [
            "Registro de não conformidades e ações corretivas",
            "Verificação de eficácia das ações",
            "Histórico de melhorias do SGSI",
        ],
    },
    # ---- A.5 Organizacional ----
    "A.5.1": {
        "como_avaliar": [
            "Existe política de SI e políticas específicas por tema, aprovadas pela direção?",
            "As políticas são comunicadas e há registro de ciência dos colaboradores?",
            "Há revisão em intervalos planejados ou após mudanças significativas?",
        ],
        "evidencias_esperadas": [
            "Política de SI e políticas temáticas aprovadas",
            "Registros de comunicação/ciência",
            "Histórico de revisão das políticas",
        ],
    },
    "A.5.2": {
        "como_avaliar": [
            "Papéis e responsabilidades de SI estão definidos e documentados?",
            "Há designação formal (ex.: coordenador/responsável pelo SGSI)?",
        ],
        "evidencias_esperadas": [
            "Documento de papéis e responsabilidades",
            "Designações formais / descrições de cargo com responsabilidades de SI",
        ],
    },
    "A.5.3": {
        "como_avaliar": [
            "Funções conflitantes foram identificadas e segregadas?",
            "Quando a segregação não é viável, há controles compensatórios?",
        ],
        "evidencias_esperadas": [
            "Matriz de segregação de funções",
            "Registros de controles compensatórios aprovados",
        ],
    },
    "A.5.4": {
        "como_avaliar": [
            "A direção exige e acompanha o cumprimento das responsabilidades de SI?",
        ],
        "evidencias_esperadas": [
            "Comunicações/atas em que a direção cobra adesão à SI",
        ],
    },
    "A.5.5": {
        "como_avaliar": [
            "Há contatos formais com autoridades relevantes (ex.: ANPD, CERT)?",
        ],
        "evidencias_esperadas": [
            "Lista de contatos com autoridades e procedimento de acionamento",
        ],
    },
    "A.5.6": {
        "como_avaliar": [
            "A organização participa de grupos/fóruns especializados de SI?",
        ],
        "evidencias_esperadas": [
            "Registros de participação em grupos de interesse/fóruns",
        ],
    },
    "A.5.7": {
        "como_avaliar": [
            "Há coleta e análise de informações sobre ameaças (threat intelligence)?",
            "A inteligência de ameaças alimenta decisões de segurança?",
        ],
        "evidencias_esperadas": [
            "Fontes/feeds de inteligência de ameaças",
            "Relatórios e ações derivadas da análise de ameaças",
        ],
    },
    "A.5.8": {
        "como_avaliar": [
            "Requisitos de SI são incorporados na gestão de projetos?",
        ],
        "evidencias_esperadas": [
            "Checklist/critérios de SI no fluxo de projetos",
        ],
    },
    "A.5.9": {
        "como_avaliar": [
            "Existe inventário de informações e ativos associados, com proprietários?",
            "O inventário é mantido atualizado?",
        ],
        "evidencias_esperadas": [
            "Inventário de ativos com proprietário e classificação",
            "Registro de atualização/revisão do inventário",
        ],
    },
    "A.5.10": {
        "como_avaliar": [
            "Há regras de uso aceitável de informações e ativos, comunicadas aos usuários?",
        ],
        "evidencias_esperadas": [
            "Política de uso aceitável e registro de ciência",
        ],
    },
    "A.5.11": {
        "como_avaliar": [
            "Há processo de devolução de ativos no desligamento/fim de contrato?",
        ],
        "evidencias_esperadas": [
            "Termo/checklist de devolução de ativos",
        ],
    },
    "A.5.12": {
        "como_avaliar": [
            "Existe esquema de classificação da informação (C/I/D)?",
            "As informações são classificadas conforme o esquema?",
        ],
        "evidencias_esperadas": [
            "Esquema de classificação documentado",
            "Exemplos de informações classificadas",
        ],
    },
    "A.5.13": {
        "como_avaliar": [
            "Há procedimento de rotulagem conforme a classificação?",
        ],
        "evidencias_esperadas": [
            "Procedimento de rotulagem e exemplos de rótulos aplicados",
        ],
    },
    "A.5.14": {
        "como_avaliar": [
            "Transferências de informação seguem regras/acordos (interno e externo)?",
            "Há proteção adequada durante a transferência?",
        ],
        "evidencias_esperadas": [
            "Política/acordos de transferência de informação",
            "Configurações de canais seguros (ex.: e-mail seguro, SFTP)",
        ],
    },
    "A.5.15": {
        "como_avaliar": [
            "Existe política de controle de acesso (físico e lógico)?",
            "As regras de acesso seguem o princípio do menor privilégio?",
        ],
        "evidencias_esperadas": [
            "Política de controle de acesso",
            "Matriz de perfis/permissões",
        ],
    },
    "A.5.16": {
        "como_avaliar": [
            "O ciclo de vida das identidades é gerenciado (criação→remoção)?",
        ],
        "evidencias_esperadas": [
            "Procedimento de gestão de identidades e registros de provisionamento",
        ],
    },
    "A.5.17": {
        "como_avaliar": [
            "Informações de autenticação (senhas/segredos) são alocadas e geridas com segurança?",
        ],
        "evidencias_esperadas": [
            "Política de senhas/segredos e uso de cofre de segredos",
        ],
    },
    "A.5.18": {
        "como_avaliar": [
            "Direitos de acesso são provisionados, revisados e revogados periodicamente?",
        ],
        "evidencias_esperadas": [
            "Registros de concessão/revogação e revisões periódicas de acesso",
        ],
    },
    "A.5.19": {
        "como_avaliar": [
            "Riscos de SI no uso de fornecedores são identificados e tratados?",
        ],
        "evidencias_esperadas": [
            "Processo de gestão de risco de fornecedores e avaliações realizadas",
        ],
    },
    "A.5.20": {
        "como_avaliar": [
            "Os contratos com fornecedores incluem requisitos de SI?",
        ],
        "evidencias_esperadas": [
            "Cláusulas de SI em contratos/acordos com fornecedores",
        ],
    },
    "A.5.21": {
        "como_avaliar": [
            "Riscos de SI na cadeia de suprimentos de TIC são gerenciados?",
        ],
        "evidencias_esperadas": [
            "Requisitos de SI para produtos/serviços de TIC e seu acompanhamento",
        ],
    },
    "A.5.22": {
        "como_avaliar": [
            "O desempenho e as mudanças de fornecedores são monitorados regularmente?",
        ],
        "evidencias_esperadas": [
            "Relatórios de monitoramento/SLA e atas de revisão de fornecedores",
        ],
    },
    "A.5.23": {
        "como_avaliar": [
            "Há processo para aquisição, uso e saída de serviços em nuvem com requisitos de SI?",
        ],
        "evidencias_esperadas": [
            "Política de uso de nuvem e avaliações de provedores (ex.: AWS)",
        ],
    },
    "A.5.24": {
        "como_avaliar": [
            "Existe plano de gestão de incidentes com papéis e responsabilidades?",
        ],
        "evidencias_esperadas": [
            "Plano/procedimento de gestão de incidentes",
        ],
    },
    "A.5.25": {
        "como_avaliar": [
            "Eventos de SI são avaliados e classificados como incidente quando aplicável?",
        ],
        "evidencias_esperadas": [
            "Critérios de classificação e registros de triagem de eventos",
        ],
    },
    "A.5.26": {
        "como_avaliar": [
            "A resposta a incidentes segue procedimentos definidos?",
        ],
        "evidencias_esperadas": [
            "Registros de tratamento de incidentes",
        ],
    },
    "A.5.27": {
        "como_avaliar": [
            "Lições aprendidas de incidentes alimentam melhorias nos controles?",
        ],
        "evidencias_esperadas": [
            "Relatórios pós-incidente e ações de melhoria",
        ],
    },
    "A.5.28": {
        "como_avaliar": [
            "Há procedimentos para coleta e preservação de evidências?",
        ],
        "evidencias_esperadas": [
            "Procedimento de cadeia de custódia/coleta de evidências",
        ],
    },
    "A.5.29": {
        "como_avaliar": [
            "A SI é mantida durante disrupções (planos de contingência)?",
        ],
        "evidencias_esperadas": [
            "Plano de continuidade considerando a SI",
        ],
    },
    "A.5.30": {
        "como_avaliar": [
            "A prontidão de TIC para continuidade é planejada e testada?",
        ],
        "evidencias_esperadas": [
            "Plano de continuidade de TIC e registros de testes",
        ],
    },
    "A.5.31": {
        "como_avaliar": [
            "Requisitos legais, regulatórios e contratuais de SI estão identificados e atualizados?",
        ],
        "evidencias_esperadas": [
            "Inventário de requisitos legais/contratuais (ex.: LGPD, contratos)",
        ],
    },
    "A.5.32": {
        "como_avaliar": [
            "Há controles para proteger direitos de propriedade intelectual e licenças?",
        ],
        "evidencias_esperadas": [
            "Inventário de licenças e procedimento de conformidade de software",
        ],
    },
    "A.5.33": {
        "como_avaliar": [
            "Registros são protegidos contra perda, falsificação e acesso não autorizado?",
        ],
        "evidencias_esperadas": [
            "Política de retenção/proteção de registros",
        ],
    },
    "A.5.34": {
        "como_avaliar": [
            "Requisitos de privacidade e proteção de PII são atendidos (ex.: LGPD)?",
        ],
        "evidencias_esperadas": [
            "Registro de operações de tratamento (ROPA) e medidas de proteção de PII",
        ],
    },
    "A.5.35": {
        "como_avaliar": [
            "Há revisão independente da segurança da informação em intervalos planejados?",
        ],
        "evidencias_esperadas": [
            "Relatórios de revisão independente/auditoria externa",
        ],
    },
    "A.5.36": {
        "como_avaliar": [
            "A conformidade com políticas e normas de SI é verificada regularmente?",
        ],
        "evidencias_esperadas": [
            "Relatórios de verificação de conformidade interna",
        ],
    },
    "A.5.37": {
        "como_avaliar": [
            "Procedimentos operacionais estão documentados e disponíveis a quem precisa?",
        ],
        "evidencias_esperadas": [
            "Procedimentos operacionais documentados e acessíveis",
        ],
    },
    # ---- A.6 Pessoas ----
    "A.6.1": {
        "como_avaliar": [
            "Há verificação de antecedentes na contratação, conforme a legislação?",
        ],
        "evidencias_esperadas": [
            "Procedimento e registros de triagem de candidatos",
        ],
    },
    "A.6.2": {
        "como_avaliar": [
            "Os contratos declaram as responsabilidades de SI do colaborador e da organização?",
        ],
        "evidencias_esperadas": [
            "Cláusulas de SI em contratos de trabalho/prestação de serviço",
        ],
    },
    "A.6.3": {
        "como_avaliar": [
            "Há programa contínuo de conscientização e treinamento em SI?",
            "A eficácia do treinamento é medida?",
        ],
        "evidencias_esperadas": [
            "Plano e registros de treinamento/conscientização",
            "Resultados de avaliações ou campanhas (ex.: phishing simulado)",
        ],
    },
    "A.6.4": {
        "como_avaliar": [
            "Existe processo disciplinar formal para violações de SI, comunicado aos colaboradores?",
        ],
        "evidencias_esperadas": [
            "Processo disciplinar documentado e comunicado",
        ],
    },
    "A.6.5": {
        "como_avaliar": [
            "Responsabilidades de SI que permanecem após o desligamento são definidas e comunicadas?",
        ],
        "evidencias_esperadas": [
            "Termo de desligamento com obrigações de SI remanescentes",
        ],
    },
    "A.6.6": {
        "como_avaliar": [
            "Há acordos de confidencialidade/NDA assinados e revisados periodicamente?",
        ],
        "evidencias_esperadas": [
            "Modelos e registros de NDAs assinados",
        ],
    },
    "A.6.7": {
        "como_avaliar": [
            "O trabalho remoto tem medidas de segurança definidas e aplicadas?",
        ],
        "evidencias_esperadas": [
            "Política de trabalho remoto e controles técnicos (VPN, MDM)",
        ],
    },
    "A.6.8": {
        "como_avaliar": [
            "Há canal para relato de eventos de SI, conhecido pelos colaboradores?",
        ],
        "evidencias_esperadas": [
            "Canal de reporte e registros de eventos relatados",
        ],
    },
    # ---- A.7 Físico ----
    "A.7.1": {
        "como_avaliar": ["Há perímetros de segurança física definidos para áreas sensíveis?"],
        "evidencias_esperadas": ["Planta de perímetros e controles de fronteira"],
    },
    "A.7.2": {
        "como_avaliar": ["O acesso físico a áreas seguras é controlado e registrado?"],
        "evidencias_esperadas": ["Logs de entrada/crachá e procedimento de acesso físico"],
    },
    "A.7.3": {
        "como_avaliar": ["Escritórios, salas e instalações têm segurança física projetada?"],
        "evidencias_esperadas": ["Layout e medidas de segurança das instalações"],
    },
    "A.7.4": {
        "como_avaliar": ["Há monitoramento físico contínuo (ex.: CFTV, alarmes)?"],
        "evidencias_esperadas": ["Registros de monitoramento e câmeras"],
    },
    "A.7.5": {
        "como_avaliar": ["Existe proteção contra ameaças físicas e ambientais?"],
        "evidencias_esperadas": ["Medidas anti-incêndio/inundação; avaliação de riscos físicos"],
    },
    "A.7.6": {
        "como_avaliar": ["Há regras para trabalho em áreas seguras?"],
        "evidencias_esperadas": ["Procedimento de trabalho em áreas seguras"],
    },
    "A.7.7": {
        "como_avaliar": ["Política de mesa limpa e tela limpa está definida e aplicada?"],
        "evidencias_esperadas": ["Política de mesa/tela limpa e evidências de adesão"],
    },
    "A.7.8": {
        "como_avaliar": ["Equipamentos são posicionados e protegidos contra ameaças?"],
        "evidencias_esperadas": ["Padrões de instalação/proteção de equipamentos"],
    },
    "A.7.9": {
        "como_avaliar": ["Ativos fora das instalações têm proteção adequada?"],
        "evidencias_esperadas": ["Política de uso de ativos externos e controles aplicados"],
    },
    "A.7.10": {
        "como_avaliar": ["Mídias de armazenamento são geridas em todo o ciclo de vida?"],
        "evidencias_esperadas": ["Procedimento de manuseio/descarte de mídias"],
    },
    "A.7.11": {
        "como_avaliar": ["Há proteção das utilidades de suporte (energia, refrigeração)?"],
        "evidencias_esperadas": ["No-breaks/geradores e registros de manutenção"],
    },
    "A.7.12": {
        "como_avaliar": ["O cabeamento de energia e dados é protegido?"],
        "evidencias_esperadas": ["Projeto/proteção de cabeamento estruturado"],
    },
    "A.7.13": {
        "como_avaliar": ["Equipamentos recebem manutenção adequada?"],
        "evidencias_esperadas": ["Plano e registros de manutenção"],
    },
    "A.7.14": {
        "como_avaliar": ["Há descarte/reutilização segura com remoção de dados?"],
        "evidencias_esperadas": ["Procedimento de sanitização e certificados de descarte"],
    },
    # ---- A.8 Tecnológico ----
    "A.8.1": {
        "como_avaliar": ["Dispositivos de endpoint têm proteção (cifragem, antimalware, MDM)?"],
        "evidencias_esperadas": ["Configuração de endpoints e política de dispositivos"],
    },
    "A.8.2": {
        "como_avaliar": ["Acessos privilegiados são restritos, controlados e monitorados?"],
        "evidencias_esperadas": ["Inventário de contas privilegiadas e logs de uso"],
    },
    "A.8.3": {
        "como_avaliar": ["O acesso à informação segue a política de controle de acesso?"],
        "evidencias_esperadas": ["Configuração de permissões por sistema"],
    },
    "A.8.4": {
        "como_avaliar": ["O acesso ao código-fonte é restrito e gerenciado?"],
        "evidencias_esperadas": ["Permissões do repositório e revisão de acessos"],
    },
    "A.8.5": {
        "como_avaliar": ["A autenticação é segura (ex.: MFA) conforme o risco?"],
        "evidencias_esperadas": ["Configuração de MFA e política de autenticação"],
    },
    "A.8.6": {
        "como_avaliar": ["A capacidade é monitorada e projetada para necessidades futuras?"],
        "evidencias_esperadas": ["Métricas de capacidade e plano de capacidade"],
    },
    "A.8.7": {
        "como_avaliar": ["Há proteção contra malware com conscientização de usuários?"],
        "evidencias_esperadas": ["Solução antimalware e cobertura/atualização"],
    },
    "A.8.8": {
        "como_avaliar": ["Vulnerabilidades técnicas são identificadas e tratadas em tempo hábil?"],
        "evidencias_esperadas": ["Relatórios de varredura e gestão de patches"],
    },
    "A.8.9": {
        "como_avaliar": ["Configurações (incl. segurança) são definidas e mantidas?"],
        "evidencias_esperadas": ["Baselines de configuração e verificação de conformidade"],
    },
    "A.8.10": {
        "como_avaliar": ["Informações são excluídas com segurança quando não mais necessárias?"],
        "evidencias_esperadas": ["Política de retenção/exclusão e registros"],
    },
    "A.8.11": {
        "como_avaliar": ["Há mascaramento de dados sensíveis quando aplicável?"],
        "evidencias_esperadas": ["Regras de mascaramento em ambientes não produtivos"],
    },
    "A.8.12": {
        "como_avaliar": ["Existem medidas de prevenção de vazamento de dados (DLP)?"],
        "evidencias_esperadas": ["Configuração de DLP e regras aplicadas"],
    },
    "A.8.13": {
        "como_avaliar": ["Backups são realizados e testados regularmente?"],
        "evidencias_esperadas": ["Política de backup e registros de testes de restauração"],
    },
    "A.8.14": {
        "como_avaliar": ["Há redundância suficiente para os requisitos de disponibilidade?"],
        "evidencias_esperadas": ["Arquitetura de redundância e testes de failover"],
    },
    "A.8.15": {
        "como_avaliar": ["Logs relevantes são produzidos, protegidos e analisados?"],
        "evidencias_esperadas": ["Política de logging e retenção; amostras de logs"],
    },
    "A.8.16": {
        "como_avaliar": ["Redes/sistemas são monitorados para comportamento anômalo?"],
        "evidencias_esperadas": ["Solução de monitoramento/SIEM e alertas"],
    },
    "A.8.17": {
        "como_avaliar": ["Os relógios dos sistemas são sincronizados com fonte confiável?"],
        "evidencias_esperadas": ["Configuração de NTP"],
    },
    "A.8.18": {
        "como_avaliar": ["O uso de utilitários privilegiados é restrito e monitorado?"],
        "evidencias_esperadas": ["Lista de utilitários e controles de uso"],
    },
    "A.8.19": {
        "como_avaliar": ["A instalação de software em sistemas é controlada?"],
        "evidencias_esperadas": ["Política de instalação e listas de software permitido"],
    },
    "A.8.20": {
        "como_avaliar": ["As redes e seus componentes são protegidos?"],
        "evidencias_esperadas": ["Topologia, firewall e regras de rede"],
    },
    "A.8.21": {
        "como_avaliar": ["Os serviços de rede têm requisitos de segurança definidos e monitorados?"],
        "evidencias_esperadas": ["Acordos de nível de serviço de rede e monitoramento"],
    },
    "A.8.22": {
        "como_avaliar": ["Há segregação de redes (ex.: VLANs, zonas)?"],
        "evidencias_esperadas": ["Segmentação de rede documentada"],
    },
    "A.8.23": {
        "como_avaliar": ["O acesso a sites externos é filtrado?"],
        "evidencias_esperadas": ["Solução de filtragem web e regras"],
    },
    "A.8.24": {
        "como_avaliar": [
            "Existe política/norma de uso de criptografia (em trânsito e em repouso)?",
            "O gerenciamento de chaves está definido (geração, rotação, guarda, revogação)?",
            "Há evidência de uso consistente nos sistemas relevantes?",
        ],
        "evidencias_esperadas": [
            "Política de criptografia e padrão de gestão de chaves",
            "Configuração de TLS/VPN/cifragem de banco ou storage",
            "Registro de exceções aprovadas",
        ],
    },
    "A.8.25": {
        "como_avaliar": ["Há ciclo de vida de desenvolvimento seguro definido?"],
        "evidencias_esperadas": ["Política/processo de SDLC seguro"],
    },
    "A.8.26": {
        "como_avaliar": ["Requisitos de segurança de aplicações são definidos e aprovados?"],
        "evidencias_esperadas": ["Requisitos de segurança nas especificações de aplicações"],
    },
    "A.8.27": {
        "como_avaliar": ["Princípios de engenharia de sistemas seguros são aplicados?"],
        "evidencias_esperadas": ["Padrões de arquitetura segura"],
    },
    "A.8.28": {
        "como_avaliar": ["Princípios de codificação segura são adotados?"],
        "evidencias_esperadas": ["Guia de codificação segura e análise estática (SAST)"],
    },
    "A.8.29": {
        "como_avaliar": ["Há testes de segurança no desenvolvimento e na aceitação?"],
        "evidencias_esperadas": ["Resultados de testes de segurança (ex.: DAST/pentest)"],
    },
    "A.8.30": {
        "como_avaliar": ["O desenvolvimento terceirizado é dirigido e monitorado?"],
        "evidencias_esperadas": ["Requisitos contratuais de SI e revisões do fornecedor"],
    },
    "A.8.31": {
        "como_avaliar": ["Ambientes de desenvolvimento, teste e produção são separados?"],
        "evidencias_esperadas": ["Evidência de segregação de ambientes"],
    },
    "A.8.32": {
        "como_avaliar": ["Mudanças são submetidas a gerenciamento formal?"],
        "evidencias_esperadas": ["Processo de gestão de mudanças e registros"],
    },
    "A.8.33": {
        "como_avaliar": ["As informações de teste são selecionadas e protegidas?"],
        "evidencias_esperadas": ["Procedimento de dados de teste e mascaramento"],
    },
    "A.8.34": {
        "como_avaliar": ["Testes de auditoria em sistemas operacionais são planejados e acordados?"],
        "evidencias_esperadas": ["Plano de testes de auditoria acordado"],
    },
}

# Legenda global de Status e Prioridade (Feature 007) — definições PT-BR originais (4 + 4).
LEGEND_DEFS: list[dict] = [
    {"kind": "status", "code": "not_meet", "label": "Não atende", "order": 1,
     "definition": "O requisito ou controle não existe na organização. Lacuna completa — deve ser implementado do zero."},
    {"kind": "status", "code": "partial", "label": "Atende Parcialmente", "order": 2,
     "definition": "Existe prática informal ou parcial, sem documentação sistemática ou sem evidências de operação regular."},
    {"kind": "status", "code": "meets", "label": "Atende Totalmente", "order": 3,
     "definition": "Implementado, documentado e com evidências de operação. Um auditor encontraria conformidade."},
    {"kind": "status", "code": "not_applicable", "label": "Não Aplicável", "order": 4,
     "definition": "Não se aplica ao escopo definido. Deve ser justificado na Declaração de Aplicabilidade (SoA)."},
    {"kind": "priority", "code": "critical", "label": "Crítica", "order": 1,
     "definition": "Lacuna que inviabiliza a certificação ou expõe a risco alto. Tratar com urgência."},
    {"kind": "priority", "code": "high", "label": "Alta", "order": 2,
     "definition": "Lacuna relevante a tratar durante o projeto; pode gerar não conformidade na auditoria se não resolvida."},
    {"kind": "priority", "code": "medium", "label": "Média", "order": 3,
     "definition": "Oportunidade de melhoria recomendada, mas não crítica para a certificação inicial."},
    {"kind": "priority", "code": "low", "label": "Baixa", "order": 4,
     "definition": "Ação de melhoria contínua; pode ser tratada no ciclo pós-certificação."},
]


def _referencia(ref_code: str, dimension: GapDimension) -> str:
    if dimension == GapDimension.clause:
        return f"ISO/IEC 27001:2022 — Cláusula {ref_code}"
    return f"ISO/IEC 27001:2022 — {ref_code}"


def _with_guidance(item: dict) -> dict:
    """Acrescenta `referencia` (derivada) + orientação do GUIDANCE (vazia se não houver)."""
    g = GUIDANCE.get(item["ref_code"], {})
    return {
        **item,
        "referencia": _referencia(item["ref_code"], item["dimension"]),
        "como_avaliar": list(g.get("como_avaliar", [])),
        "evidencias_esperadas": list(g.get("evidencias_esperadas", [])),
        "nota": g.get("nota"),
    }


def build_seed_items() -> list[dict]:
    """Retorna lista de dicts para inserção em `gap_seed_item` (sem id nem seed_version_id)."""
    items: list[dict] = []

    # Cláusulas
    for c in CLAUSES:
        items.append(_with_guidance({**c}))

    # A.5 — organizacional
    for ref, name, objective, order in A5_CONTROLS:
        items.append(_with_guidance({
            "ref_code": ref, "name": name, "dimension": GapDimension.annex_a,
            "theme": GapTheme.organizational, "objective": objective, "order": 100 + order,
        }))

    # A.6 — pessoas
    for ref, name, objective, order in A6_CONTROLS:
        items.append(_with_guidance({
            "ref_code": ref, "name": name, "dimension": GapDimension.annex_a,
            "theme": GapTheme.people, "objective": objective, "order": 200 + order,
        }))

    # A.7 — físico
    for ref, name, objective, order in A7_CONTROLS:
        items.append(_with_guidance({
            "ref_code": ref, "name": name, "dimension": GapDimension.annex_a,
            "theme": GapTheme.physical, "objective": objective, "order": 300 + order,
        }))

    # A.8 — tecnológico
    for ref, name, objective, order in A8_CONTROLS:
        items.append(_with_guidance({
            "ref_code": ref, "name": name, "dimension": GapDimension.annex_a,
            "theme": GapTheme.technological, "objective": objective, "order": 400 + order,
        }))

    return items

