{
    'name': 'Language Core',
    'version': '18.0.1.0.0',
    'category': 'Custom/Lexora',
    'summary': 'Core infrastructure: system parameters, job status mixin, RabbitMQ publisher stub',
    'author': 'Lexora',
    'license': 'LGPL-3',
    'depends': ['language_security', 'web_notify'],
    'data': [
        'security/ir.model.access.csv',
        'data/system_parameters.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
