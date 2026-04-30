{
    "name": "Lexora AI Helpdesk",
    "version": "1.0.0",
    "summary": "100% automated helpdesk — every ticket auto-answered by OdooBot via RAG.",
    "description": """
        Intercepts helpdesk.ticket creation and calls the ai_mentor FastAPI service
        (RAG pipeline: pgvector retrieval + llama-cpp LLM generation). The generated
        reply is injected into the ticket chatter as an OdooBot message.
        No human agents required in the default configuration.
    """,
    "author": "Avantgarde Systems",
    "category": "Hidden",
    "license": "LGPL-3",
    "depends": ["helpdesk", "mail"],
    "data": [
        "data/ir_config_parameter.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
