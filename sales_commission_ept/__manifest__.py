{
    'name': 'Sales Commission',
    'version': '',
    'summary': 'Commissions and Commission lines of Sales Persons.',
    'author': 'Emipro Technologies (P) Ltd.',
    'depends': ['sale'],
    'data': ['security/security.xml',
             'security/ir.model.access.csv',
             'data/sale_commission_sequence.xml',
             'views/sales_commission.xml',
             'views/sales_commissions_lines.xml',
             'views/res_config_settings.xml',
             'wizard/wizard_sales_commission.xml',
             'data/scheduled_action.xml',
             'views/menu.xml'],
    'installable': True,
    'auto_install': False
}
