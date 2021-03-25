{
    'name': 'Sales Commission',
    'version': '1.0',
    'license': 'OPL-1',
    'summary': 'Commissions',
    'author': 'Emipro Technologies (P) Ltd.',
    'depends': ['sale'],
    'data': ['security/security.xml',
             'security/ir.model.access.csv',
             'data/sale_commission_sequence.xml',
             'views/sales_commission.xml',
             'views/sales_commissions_lines.xml',
             'views/res_config_settings.xml',
             'wizard/wizard_sales_commission.xml',
             'views/menu.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False
}

