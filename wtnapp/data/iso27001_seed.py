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


def build_seed_items() -> list[dict]:
    """Retorna lista de dicts para inserção em `gap_seed_item` (sem id nem seed_version_id)."""
    items: list[dict] = []

    # Cláusulas
    for c in CLAUSES:
        items.append({**c})

    # A.5 — organizacional
    for ref, name, objective, order in A5_CONTROLS:
        items.append({
            "ref_code": ref,
            "name": name,
            "dimension": GapDimension.annex_a,
            "theme": GapTheme.organizational,
            "objective": objective,
            "order": 100 + order,
        })

    # A.6 — pessoas
    for ref, name, objective, order in A6_CONTROLS:
        items.append({
            "ref_code": ref,
            "name": name,
            "dimension": GapDimension.annex_a,
            "theme": GapTheme.people,
            "objective": objective,
            "order": 200 + order,
        })

    # A.7 — físico
    for ref, name, objective, order in A7_CONTROLS:
        items.append({
            "ref_code": ref,
            "name": name,
            "dimension": GapDimension.annex_a,
            "theme": GapTheme.physical,
            "objective": objective,
            "order": 300 + order,
        })

    # A.8 — tecnológico
    for ref, name, objective, order in A8_CONTROLS:
        items.append({
            "ref_code": ref,
            "name": name,
            "dimension": GapDimension.annex_a,
            "theme": GapTheme.technological,
            "objective": objective,
            "order": 400 + order,
        })

    return items
