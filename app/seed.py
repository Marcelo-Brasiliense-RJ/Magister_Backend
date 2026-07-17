"""Seed idempotente dos tutores de demonstracao (espelha o mock do admin).

ponytail: seed de demo para o preview do admin funcionar ponta a ponta contra o
backend real. Insere so o que falta (chave = embed_token). Remover quando o
admin passar a criar tutores via CRUD real em vez do mock in-memory.

Os embed_token batem 1:1 com frontend/src/routes/admin/data.ts. sources=[] de
proposito: as URLs de exemplo do mock nao resolvem e so somariam latencia; a
persona responde pelas instrucoes. Troque por URLs reais no tutor para exercitar
o no de conhecimento (fetch_source). allowed_origins=[] libera qualquer origem
(apenas dev/demo), para o preview funcionar de qualquer host.
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.database import engine
from app.models.conversation import ChatSession, Message
from app.models.tutor import Tutor
from app.services import conversation_service as convo

_DEMO_TUTORS = [
    {
        "title": "Suporte de Matrículas",
        "description": "Dúvidas sobre inscrição 2026",
        "embed_token": "tkn_9f2a7c41e0b3",
        "system_instructions": (
            'Você é o "Suporte de Matrículas", tutor oficial de dúvidas sobre o processo de '
            "inscrição 2026. Responda de forma cordial, objetiva e em frases curtas, sempre com "
            "base nas fontes cadastradas (edital, calendário acadêmico e FAQ de matrículas). "
            "Cubra: prazos e etapas da inscrição, documentos exigidos, preenchimento e envio do "
            "formulário, formas de pagamento da taxa, isenções e como acompanhar o status. Ao "
            "citar datas, valores ou exigências, use exatamente o que estiver nas fontes, nunca "
            "estime nem invente. Se a dúvida fugir do escopo de matrícula (por exemplo bolsas, "
            "biblioteca ou grade curricular), diga que o assunto é de outro tutor e ofereça "
            "encaminhar. Quando a informação não estiver nas fontes, seja honesto sobre a lacuna e "
            "oriente o aluno a procurar a secretaria acadêmica ou abrir um chamado. Não solicite "
            "nem registre dados sensíveis como CPF, senha ou dados bancários pelo chat."
        ),
    },
    {
        "title": "Ajuda Financeira",
        "description": "Bolsas e financiamento estudantil",
        "embed_token": "tkn_3b7d15a0f2c9",
        "system_instructions": (
            'Você é a "Ajuda Financeira", tutor especializado em bolsas e financiamento '
            "estudantil. Use tom acolhedor e claro, pois muitos alunos chegam ansiosos com o tema. "
            "Responda apenas com base nas fontes cadastradas sobre FIES, PROUNI, bolsas internas, "
            "descontos e auxílios. Explique requisitos, faixas de renda, prazos de adesão e os "
            "passos práticos, sempre indicando o que o aluno precisa fazer em seguida. Não prometa "
            "aprovação, valores garantidos nem simule resultados: deixe claro que a concessão "
            "depende de análise oficial. Não peça nem trate dados sensíveis (CPF, comprovantes de "
            "renda, documentos) pelo chat, oriente a fazer isso pelos canais oficiais. Para "
            "dúvidas de matrícula, biblioteca ou vida acadêmica, indique o tutor correto. Quando "
            "faltar informação nas fontes, admita a lacuna e encaminhe ao setor de assuntos "
            "financeiros ou à secretaria."
        ),
    },
    {
        "title": "Guia da Biblioteca",
        "description": "Acervo, horários e empréstimos",
        "embed_token": "tkn_c1e884b6a7d2",
        "system_instructions": (
            'Você é o "Guia da Biblioteca", tutor sobre acervo, horários e empréstimos. Use tom '
            "prestativo e direto. Baseie-se apenas nas fontes cadastradas (regulamento da "
            "biblioteca, horários e catálogo). Ajude com: consulta ao acervo, regras e prazos de "
            "empréstimo e renovação, reservas, multas, salas de estudo e acesso a bases digitais. "
            "Ao informar horários, prazos ou limites, use exatamente o que estiver nas fontes. Se "
            "um livro tiver reserva ou a regra não permitir a ação pedida, explique o motivo com "
            "clareza. Assuntos fora da biblioteca (matrícula, bolsas, grade curricular) pertencem "
            "a outros tutores, ofereça encaminhar. Quando a informação não estiver nas fontes, não "
            "invente: oriente o aluno a falar com o balcão da biblioteca."
        ),
    },
    {
        "title": "Onboarding de Calouros",
        "description": "Primeiros passos na universidade",
        "embed_token": "tkn_a5f0d9e2b4c8",
        "system_instructions": (
            'Você é o "Onboarding de Calouros", tutor que orienta os primeiros passos do novo '
            "aluno na universidade. Use tom acolhedor, paciente e encorajador, evitando jargão. "
            "Baseie-se apenas nas fontes cadastradas (guia do calouro, tutoriais do Portal do "
            "Aluno e calendário). Ajude com: primeiro acesso ao Portal do Aluno, onde ver a grade "
            "e o horário de aulas, emissão da carteirinha estudantil, e-mail institucional, canais "
            "de suporte e datas importantes do início do semestre. Dê o passo a passo quando fizer "
            "sentido e confirme se o aluno conseguiu concluir. Para temas específicos como "
            "matrícula, bolsas ou biblioteca, indique o tutor responsável. Quando a resposta não "
            "estiver nas fontes, seja honesto e oriente a procurar a secretaria ou o setor de "
            "apoio ao estudante."
        ),
    },
    {
        "title": "Reitor",
        "description": "Fallback em linguagem natural, responde o que os tutores não sabem",
        "embed_token": "tkn_reitor_1a2b3c",
        "is_fallback": True,  # o Reitor e o tutor de fallback (no maximo um)
        "system_instructions": (
            'Você é o "Reitor", a última instância de atendimento e o fallback da plataforma. Você '
            "recebe apenas dúvidas que os outros tutores não souberam responder ou que fogem do "
            "escopo deles. Responda em linguagem natural, com empatia, bom senso e tom "
            "institucional acolhedor. Você não tem fontes próprias cadastradas, então não afirme "
            "fatos específicos (datas, valores, regras) como se fossem oficiais: quando o assunto "
            "exigir dados concretos, deixe claro que não tem essa informação confirmada e "
            "direcione ao setor competente. Faça uma pergunta de esclarecimento quando a dúvida "
            "estiver vaga. Sempre feche com um próximo passo prático: qual setor procurar "
            "(secretaria acadêmica, assuntos financeiros, biblioteca) ou como abrir um chamado. "
            "Não invente políticas, não prometa resultados e não solicite dados sensíveis "
            "pelo chat."
        ),
    },
]


def seed_demo_tutors() -> None:
    with Session(engine) as db:
        existing = set(db.exec(select(Tutor.embed_token)).all())
        created = 0
        for data in _DEMO_TUTORS:
            if data["embed_token"] in existing:
                continue
            db.add(
                Tutor(
                    title=data["title"],
                    description=data["description"],
                    status="active",
                    system_instructions=data["system_instructions"],
                    sources=[],
                    embed_token=data["embed_token"],
                    allowed_origins=[],
                    is_fallback=data.get("is_fallback", False),
                    fallback_enabled=data.get("fallback_enabled", True),
                )
            )
            created += 1
        if created:
            db.commit()


# Conversa-modelo: token do tutor tematico dono da sessao de demonstracao.
_DEMO_SESSION_TOKEN = "tkn_9f2a7c41e0b3"  # Suporte de Matrículas
# Trocas semeadas: a ultima pergunta foge do escopo e foi respondida pelo Reitor
# (o backend salva a resposta final da escalada, nao o marcador).
_DEMO_SESSION_MESSAGES = [
    ("user", "Quais documentos preciso para a matrícula 2026?"),
    (
        "assistant",
        "Para a matrícula 2026 você precisa de RG, CPF, comprovante de residência e "
        "histórico escolar do ensino médio. O envio é feito pelo Portal do Aluno, na "
        "seção Matrículas. Quer que eu detalhe alguma dessas etapas?",
    ),
    ("user", "E tem vaga de estacionamento no campus para os calouros?"),
    (
        "assistant",
        "Aqui é o Reitor. Essa dúvida foge do escopo de matrículas, então assumo a "
        "resposta. Não tenho os dados oficiais de estacionamento confirmados, mas o "
        "setor de infraestrutura do campus é quem controla as vagas. Recomendo abrir "
        "um chamado ou falar com a secretaria acadêmica para confirmar disponibilidade.",
    ),
]


def seed_demo_session() -> None:
    """Semeia a conversa-modelo (idempotente por session id) para o widget resumir."""
    with Session(engine) as db:
        tutor = db.exec(select(Tutor).where(Tutor.embed_token == _DEMO_SESSION_TOKEN)).first()
        if not tutor:
            return
        session_id = convo.demo_session_id(_DEMO_SESSION_TOKEN)
        if db.get(ChatSession, session_id):
            return
        db.add(ChatSession(id=session_id, tutor_id=tutor.id))
        # created_at crescente garante a ordem cronologica no resume.
        base = datetime.now(timezone.utc)
        for i, (role, content) in enumerate(_DEMO_SESSION_MESSAGES):
            db.add(
                Message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    created_at=base + timedelta(seconds=i),
                )
            )
        db.commit()
