from odoo import fields, models


class SalesCommissionLine(models.Model):
    """
    This class will have commission lines. Which stores
    commission related information about sales persons.
    """

    _name = 'sales.commission.line'
    _description = 'Sales Commission Line'

    commission_id = fields.Many2one(comodel_name='sales.commission.ept',
                                    help='Sales Commission records.')
    user_id = fields.Many2one(comodel_name='res.users',
                              string='Salesperson',
                              help='Sales Person.')
    partner_id = fields.Many2many(comodel_name='res.partner',
                                  string='Customer',
                                  help='Customer Name.')
    commission_date = fields.Date(string='Date Of Commission',
                                  help='Date of source document.')
    source_document = fields.Char(string='Source Document',
                                  help='Name of document. Documents '
                                       'can be sale orders or invoices.')
    amount = fields.Float(string='Commission Amount', readonly=True,
                          digits=(6, 2), help='Salepersons Commission Amount.')
    status = fields.Selection(selection=[('Draft', 'Draft'),
                                         ('Paid', 'Paid')],
                              compute='_compute_commission_state',
                              help='State of commission.(Paid or Unpaid)',
                              default='Draft')
    paid_amount = fields.Boolean(string='Amount Paid',
                                 help='Check if commission is paid.')

    def _compute_commission_state(self):
        """
        Compute method to set the status of commission line
        based on paid_amount's boolean value.
        :return:
        """
        for line in self:
            if line.paid_amount:
                line.status = 'Paid'
            else:
                line.status = 'Draft'
