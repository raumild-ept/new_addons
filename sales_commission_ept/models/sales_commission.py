from datetime import date
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SalesCommission(models.Model):
    """
    This class has fields and methods to calculate and fetch data of
    commissions on sale orders and invoices to salespersons.

    This class have fields to calculate the commissions and have
    method to validate the date constraints, method to compute fields,
    method to get commissions lines based on system parameters and
    some button events.
    """
    _name = 'sales.commission.ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sales Commission EPT'

    name = fields.Char(default='COM/#####/GET', readonly=True, help='Commission name')
    user_id = fields.Many2one(comodel_name='res.users',
                              help='Salesperson or Salesmanager',
                              string='Salesperson',
                              default=lambda self: self.env.user)
    from_date = fields.Date(string='Commissions From')
    to_date = fields.Date(string='Commissions To', required=True)
    paid_date = fields.Date(string='Commission Paid Date')
    total_commission = fields.Float(string='Total Commission', digits=(6, 2),
                                    compute='_compute_total_commission')
    status = fields.Selection(selection=[('Draft', 'Draft'),
                                         ('Paid', 'Paid')],
                              string='Stage',

                              tracking=True,
                              default='Draft')
    commission_lines_ids = fields.One2many(comodel_name='sales.commission.line',
                                           inverse_name='commission')
    product_id = fields.Many2one(comodel_name='product.product', string='Product',
                                 readonly=True)
    salesperson_commission_calculation = fields.Selection(
        selection=[('Confirm Sales Order', 'Confirm Sales Order'),
                   ('Confirm Invoice', 'Confirm Invoice'),
                   ('Paid Invoice', 'Paid Invoice')
                   ],
        store=False,
        string='Commission Calculation')
    manager_commission_calculation = fields.Selection(
        selection=[('Individual sales', 'Individual sales'),
                   ('Team Sales', 'Team Sales')],
        string='Manager Commission Calculation',
        store=False)

    @api.model
    def create(self, vals_list):
        """
        Create method is inherited to check validation of to be added commission master.
        If dates conflict with records already present in commission master records
        than it will raise error and won't create it.

        Create method's 'vals_list' dict is altered and custom name is added to it.

        :param vals_list: It is dictionary of values inserted in form.
        :return:
        """
        user_records = self.search([('user_id', '=', vals_list['user_id'])])

        # If from_date and to_date creates conflict with existing records than it will raise error.
        if user_records.filtered(
                lambda rec: vals_list['from_date'] >= str(rec.from_date) and
                            vals_list['from_date'] <= str(rec.to_date) or
                            vals_list['to_date'] >= str(rec.from_date) and
                            vals_list['to_date'] <= str(rec.to_date) or
                            vals_list['from_date'] <= str(rec.from_date) and
                            vals_list['to_date'] >= str(rec.to_date)):
            raise ValidationError(_(
                """The dates you are setting are conflicting with existing records of
                 the Salesperson you have set."""))

        vals_list['name'] = self.env['ir.sequence'].next_by_code('sale.commission.sequence')
        return super(SalesCommission, self).create(vals_list)

    # Compute method to compute total commission.
    def _compute_total_commission(self):
        """
        This method will compute sum of all commission lines attached to the commission master.
        :return:
        """
        for record in self:
            record.total_commission = sum(map(lambda line: line.amount, self.commission_lines_ids))

    def set_to_draft(self):
        """
        This method is executed when 'Set To Draft' button is clicked. This will open
        the form view of wizard which will ask for reason why we want to change state.

        :return: dynamic action is returned which will open the wizard.
        """
        return {
            'res_model': 'wizard.sales.commission',
            'type': 'ir.actions.act_window',
            'name': _('Draft State Reason'),
            'target': 'new',
            'view_mode': 'form',
            'view_id': self.env.ref('sales_commission_ept.wizard_sales_commission_form').id
        }

    def _get_commission_lines(self):
        """
        This method
        :return:
        """
        if self.user_id in self.env['crm.team'].search([]).mapped('user_id'):
            pass
        else:
            commission_percentage = float(self.env['ir.config_parameter'].sudo().get_param(
                'sales_commission_ept.commission_percentage'))
            if self.salesperson_commission_calculation == 'Confirm Sales Order':
                sales = self.env['sale.order'].search([('user_id', '=', self.user_id.id),
                                                       ('state', '=', 'sale'),
                                                       ]).filtered(
                    lambda sale: self.product_id in sale.order_line.mapped('product_id'))
                commission_lines = list(map(lambda sale: (0, 0, {
                    'commission': self.id,
                    'user_id': self.user_id.id,
                    'commission_date': sale.sale_order_date,
                    'amount': sale.amount_total * commission_percentage,
                    'partner_id': sale.partner_id.id,
                    'source_document': sale.name}), sales))

            elif self.salesperson_commission_calculation == 'Confirm Invoice':
                invoices = self.env['account.move'].search([('user_id', '=', self.user_id.id),
                                                            ('state', '=', 'posted')]).filtered(
                    lambda inv: self.product_id in inv.invoice_line_ids.mapped('product_id'))
                commission_lines = list(map(lambda invoice: (0, 0, {
                    'commission': self.id,
                    'user_id': self.user_id.id,
                    'commission_date': invoice.invoice_date,
                    'amount': invoice.amount_total * commission_percentage,
                    'partner_id': invoice.partner_id.id,
                    'source_document': invoice.name}), invoices))
            else:
                invoices = self.env['account.move'].search([('user_id', '=', self.user_id.id),
                                                            ('payment_state', '=', 'paid')]).filtered(
                    lambda inv: self.product_id in inv.invoice_line_ids.mapped('product_id'))
                commission_lines = list(map(lambda invoice: (0, 0, {
                    'commission': self.id,
                    'user_id': self.user_id.id,
                    'commission_date': invoice.invoice_date,
                    'amount': invoice.amount_total * commission_percentage,
                    'partner_id': invoice.partner_id.id,
                    'source_document': invoice.name}), invoices))
            return commission_lines

    def calculate_commission(self):
        """
        This method will fetch all commission lines from database.
        :return:
        """
        self.commission_lines_ids.unlink()
        self.status = 'Draft'
        commission_lines = self._get_commission_lines()
        self.write({
            'commission_lines_ids': commission_lines
        })

    @api.onchange('commission_lines_ids')
    def set_status(self):
        """
        When 'commission_lines_ids' field is altered this method
        have functionality to change status to 'Paid' or 'Draft'.
        :return:
        """
        check_list = self.commission_lines_ids.mapped('paid_amount')
        if check_list and False not in check_list:
            self.status = 'Paid'
            self.paid_date = date.today()
        else:
            self.status = 'Draft'
            self.paid_date = False

    def paid_commission(self):
        """
        This method will set all commission lines paid_amount checkbox to True
        and commission masters's state will be changed to 'Paid'.

        This method will be change state of all commissions to paid.
        :return:
        """
        self.commission_lines_ids.paid_amount = True
        self.status = 'Paid'
