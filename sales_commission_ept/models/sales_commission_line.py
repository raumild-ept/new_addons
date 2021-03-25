from odoo import fields, models, api


class SalesCommissionLine(models.Model):
    """
    This class will have commission lines. Which stores
    commission related information about sales persons.
    """
    
    _name = 'sales.commission.line'
    _description = 'Sales Commission Line'

    commission = fields.Many2one(comodel_name='sales.commission.ept')
    user_id = fields.Many2one(comodel_name='res.users',
                              string='Salesperson')
    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Customer')
    commission_date = fields.Date(string='Commission Date')
    source_document = fields.Char(string='Source Document')
    amount = fields.Float(string='Amount', readonly=True, digits=(6, 2))
    status = fields.Selection(selection=[('Draft', 'Draft'),
                                         ('Paid', 'Paid')],
                              compute='_compute_commission_state',
                              default='Draft')
    paid_amount = fields.Boolean(string='Amount Paid')


    def _compute_commission_state(self):
        """
        Compute method to set the status of commission line.
        :return:
        """
        for line in self:
            if line.paid_amount == True:
                line.status = 'Paid'
            else:
                line.status = 'Draft'
