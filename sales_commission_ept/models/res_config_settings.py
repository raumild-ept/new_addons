from odoo import fields, models


class ResConfigSettingsExtended(models.TransientModel):
    """
    This class inherits fields and functionality of model 'res.config.settings'.
    Here for requirement of module sales_commission_ept we are adding few fields to it.
    """
    _inherit = 'res.config.settings'

    default_salesperson_commission_calculation = fields.Selection(
        selection=[('Confirm Sales Order', 'Confirm Sales Order'),
                   ('Confirm Invoice', 'Confirm Invoice'),
                   ('Paid Invoice', 'Paid Invoice')
                   ],
        help='Commission counting method for commission users.',
        default_model='sales.commission.ept',
        string='Commission Calculation')

    default_manager_commission_calculation = fields.Selection(
        selection=[('Individual sales', 'Individual sales'),
                   ('Team Sales', 'Team Sales')],
        string='Manager Commission Calculation',
        help='Commission counting method for commission managers.',
        default_model='sales.commission.ept')

    commission_percentage = fields.Float(
        string='Commission Percentage',
        digits=(2, 2),
        help='Default commission percentage.',
        config_parameter='sales_commission_ept.commission_percentage')

    team_commission_percentage = fields.Float(
        string='Team Commission Percentage', digits=(2, 2),
        config_parameter='sales_commission_ept.sales_team_commission_percentage',
        help="Commission percentage on sales team's total amount.")

    default_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Commission Product',
        help='Commission product on which commissions are calculated.',
        default_model='sales.commission.ept')
