{
    'name': 'Language Enrichment',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'LLM enrichment model and async job lifecycle (Qwen3)',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_words', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/enrichment_record_rules.xml',
        'data/ir_cron_enrichment.xml',
        'views/language_enrichment_views.xml',
        'views/portal_enrichment.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
