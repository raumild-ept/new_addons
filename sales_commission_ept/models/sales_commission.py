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

    name = fields.Char(default='COM/#####/GET', readonly=True,
                       help='Commission name')
    user_id = fields.Many2one(comodel_name='res.users',
                              help='Salesperson or Salesmanager',
                              string='Salesperson',
                              default=lambda self: self.env.user)
    from_date = fields.Date(string='Commissions From',
                            help='Select starting date.')
    to_date = fields.Date(string='Commissions To', required=True,
                          help='Select ending date.')
    paid_date = fields.Date(string='Commission Paid Date',
                            help='Date on which all commissions are paid.')
    total_commission = fields.Float(string='Commission Total', digits=(6, 2),
                                    compute='_compute_total_commission',
                                    help='Total commission of salesperson.')
    status = fields.Selection(selection=[('Draft', 'Draft'),
                                         ('Paid', 'Paid')],
                              string='State',
                              tracking=True,
                              default='Draft',
                              help='State of Sales Commission')
    commission_lines_ids = fields.One2many(comodel_name='sales.commission.line',
                                           inverse_name='commission_id',
                                           help='Commission lines of salesperson.')
    product_id = fields.Many2one(comodel_name='product.product', string='Product',
                                 readonly=True, help='Commission Product.')
    salesperson_commission_calculation = fields.Selection(
        selection=[('Confirm Sales Order', 'Confirm Sales Order'),
                   ('Confirm Invoice', 'Confirm Invoice'),
                   ('Paid Invoice', 'Paid Invoice')
                   ],
        store=False,
        help='Mode of commission calculation of salesperson user.',
        string='Commission Calculation')

    manager_commission_calculation = fields.Selection(
        selection=[('Individual sales', 'Individual sales'),
                   ('Team Sales', 'Team Sales')],
        string='Manager Commission Calculation Mode',
        help='Mode of commission calculation of salesperson manager.',
        store=False)

    @api.model
    def create(self, vals_list):
        """
        Create method is inherited to check validation of to be added commission master.
        If dates conflict with records already present in commission master records
        than it will raise error and won't create it.

        If any record of selected salesperson is present in database in given time
        set (from_date and to_date), than it wont allow to create commission master.

        Create method's 'vals_list' dict is altered and custom name is added to it.

        :param vals_list: It is dictionary of values inserted in form.
        :return:
        """
        user_records = self.search([('user_id', '=', vals_list['user_id'])])

        # If from_date and to_date creates conflict with existing records than it will raise error.
        if vals_list['from_date'] and user_records.filtered(
                lambda rec: vals_list['from_date'] >= str(rec.from_date) and
                            vals_list['from_date'] <= str(rec.to_date) or
                            vals_list['to_date'] >= str(rec.from_date) and
                            vals_list['to_date'] <= str(rec.to_date) or
                            vals_list['from_date'] <= str(rec.from_date) and
                            vals_list['to_date'] >= str(rec.to_date)):
            raise ValidationError(_(
                """The dates you are setting are conflicting with existing records of
                 the Salesperson you have set. Enter the set of dates for which commission
                 records won't get duplicated.                 
                 Suggestion:- Enter From Date if you have not entered. If only To Date set,
                              it have higher chances of conflicts."""))

        if user_records.filtered(
                lambda rec: vals_list['to_date'] >= str(rec.from_date)
                            or vals_list['to_date'] >= str(rec.to_date)):
            raise ValidationError(_(
                """The dates you are setting are conflicting with existing records of
                 the Salesperson you have set. Enter the set of dates for which commission
                 records won't get duplicated.
                 Suggestion:- Enter From Date if you have not entered. If only To Date set,
                              it have higher chances of conflicts."""))

        vals_list['name'] = self.env['ir.sequence'].next_by_code('sale.commission.sequence')
        return super(SalesCommission, self).create(vals_list)

    # Compute method to compute total commission.
    def _compute_total_commission(self):
        """
        This method will compute sum of all commission lines attached to the
        commission master.

        Here computation have two methods. If sales person is sales manager and
        Manage Commission Method is set to 'Total Sales' than manager will
        have commission on whole team sales too.
        For that system parameter is configured and sales manager will get commission
        from sales team's members commissions.

        That commission will be added to his individual commissions.
        :return:
        """
        for record in self:
            sales_team = self.env['crm.team'].search([('user_id', '=', self.user_id.id)])
            if sales_team and self.manager_commission_calculation == 'Team Sales':
                team_commission_percentage = float(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'sales_commission_ept.sales_team_commission_percentage'))

                sale_manager_commission = sum(
                    map(lambda line: line.amount, self.commission_lines_ids.filtered(
                        lambda line: line.user_id == self.user_id)))

                extra_commission = sum(map(
                    lambda line: line.amount, self.commission_lines_ids.filtered(
                        lambda line: line.user_id != self.user_id
                    ))) * team_commission_percentage
                record.total_commission = sale_manager_commission + extra_commission

            else:
                record.total_commission = sum(map(
                    lambda line: line.amount, self.commission_lines_ids.filtered(
                        lambda line: line.user_id == self.user_id
                    )))

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

    def _get_paid_invoiced_commission_lines(self, commission_percentage, members, from_date):
        """
        This method will search paid invoices and will calculate commissions amount
        based on commission percentage. It will return array of commission lines.

        :param commission_percentage: -> float value of percentage of commission.

        :param members: -> list of all member's ids in sales_team of salesperson if he is sales manager.
                            if he is not sales manager than list will be empty.

        :param from_date: -> from_date is self.from_date. If self.from_date is not set than
                                from_date will have 100 years old static date and
                                based on that date constraint will be handled.

        :return: commission_lines: ->  array of commission_lines which will be set as one2many on commission master.
        """
        invoices = self.env['account.move'].search(
            [('invoice_date', '<=', self.to_date), ('invoice_date', '>=', from_date)]).filtered(
            lambda
                inv: inv.user_id.id in members or inv.user_id == self.user_id and
                     self.product_id in inv.invoice_line_ids.mapped('product_id'))
        invoice_lines = invoices.invoice_line_ids.filtered(lambda line: line.product_id == self.product_id)
        commission_lines = list(map(lambda line: (0, 0, {
            'commission_id': self.id,
            'user_id': line.move_id.user_id.id,
            'commission_date': line.move_id.invoice_date,
            'amount': line.price_subtotal * commission_percentage,
            'partner_id': [(4, line.move_id.partner_id.id)],
            'source_document': line.move_id.name}), invoice_lines))
        return commission_lines

    def _get_invoiced_commission_lines(self, commission_percentage, members, from_date):
        """
        This method will search confirmed invoices and will calculate commissions amount
        based on commission percentage. It will return array of commission lines.

        :param commission_percentage: -> float value of percentage of commission.

        :param members: -> list of all member's ids in sales_team of salesperson if he is sales manager.
                            if he is not sales manager than list will be empty.

        :param from_date: -> from_date is self.from_date. If self.from_date is not set than
                                from_date will have 100 years old static date and
                                based on that date constraint will be handled.

        :return: commission_lines: ->  array of commission_lines which will be set as one2many on commission master.
        """
        invoices = self.env['account.move'].search(
            [('invoice_date', '<=', self.to_date), ('invoice_date', '>=', from_date)]).filtered(
            lambda inv: inv.user_id.id in members or inv.user_id == self.user_id and
                        self.product_id in inv.invoice_line_ids.mapped('product_id'))

        invoice_lines = invoices.invoice_line_ids.filtered(
            lambda line: line.product_id == self.product_id)

        commission_lines = list(map(lambda line: (0, 0, {
            'commission_id': self.id,
            'user_id': line.move_id.user_id.id,
            'commission_date': line.move_id.invoice_date,
            'amount': line.price_subtotal * commission_percentage,
            'partner_id': [(4, line.move_id.partner_id.id)],
            'source_document': line.move_id.name}), invoice_lines))

        return commission_lines

    def _get_sale_commission_lines(self, commission_percentage, members, from_date):
        """
        This method will search confirmed sale orders and will calculate commissions amount
        based on commission percentage. It will return array of commission lines.

        :param commission_percentage: -> float value of percentage of commission.

        :param members: -> list of all member's ids in sales_team of salesperson
                            if he is sales manager. If he is not sales manager
                             than list will be empty.

        :param from_date: -> from_date is self.from_date. If self.from_date is not set than
                                from_date will have 100 years old static date and
                                based on that date constraint will be handled.

        :return: commission_lines: ->  array of commission_lines which will be set
                                        as one2many on commission master.
        """
        sales = self.env['sale.order'].search(
            [('sale_order_date', '<=', self.to_date),
             ('sale_order_date', '>=', from_date)]).filtered(
            lambda s:
            s.user_id.id in members or s.user_id == self.user_id and
            self.product_id in s.order_line.mapped('product_id'))

        sale_order_lines = sales.order_line.filtered(
            lambda line: line.product_id == self.product_id)
        commission_lines = list(map(lambda line: (0, 0, {
            'commission_id': self.id,
            'user_id': line.order_id.user_id.id,
            'commission_date': line.order_id.sale_order_date,
            'amount': line.price_subtotal * commission_percentage,
            'partner_id': [(4, line.order_id.partner_id.id)],
            'source_document': line.order_id.name}), sale_order_lines))
        return commission_lines

    def _get_commission_lines(self):
        """
        This method will check if selected salesperson is sales manager or team leader of
        any sales team or not. If not than commission percentage will be set to normal
        commission user's percentage value which is configured in system parameters.

        If salesperson is sales manager than it will add salesperson's all members ids
        to variable 'members'. This time commission percentage will be set as sales teams
        commission percentage value set in system parameters.

        Than here it is checked on what commissions will be calculated, for that
        we have field 'salesperson_commission_calculation' which will have mode of commission.

        On that mode different methods are called. from_date field is set if from_date field on
        commission master is set. Else it will be set to 100 years old static value
        for computation of records on which from_date is not configured.

        :return: commission_lines :-> one2many field which will be set to commission master.
        """
        from_date = self.from_date
        if not self.from_date:
            from_date = '1900-01-01'

        members = []
        commission = float(self.env['ir.config_parameter'].sudo().get_param(
            'sales_commission_ept.commission_percentage'))
        sales_team = self.env['crm.team'].search([('user_id', '=', self.user_id.id)])

        if sales_team:
            members = sales_team.member_ids.ids

        if self.salesperson_commission_calculation == 'Confirm Sales Order':
            commission_lines = self._get_sale_commission_lines(commission, members, from_date)

        elif self.salesperson_commission_calculation == 'Confirm Invoice':
            commission_lines = self._get_invoiced_commission_lines(commission, members, from_date)

        else:
            commission_lines = self._get_paid_invoiced_commission_lines(commission, members, from_date)

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

    def _set_status_to_paid(self):
        """
        Scheduled action will call this method one time per day.
        If commission master's all commission lines are paid so that
        commission master will be paid, Than it will write current
        day's date to field 'paid_date'

        :return:
        """
        if self.status == 'Paid':
            self.paid_date = date.today()

    @api.onchange('commission_lines_ids')
    def set_status(self):
        """
        It will check if all lines are checked to paid, means if they all
        are checked to paid than mapped() function will have only one
        value, that would be 'True'. If 'False' value not found in all paid_amount
        checkbox of commission lines than it will set status of commission master to paid.

        If any line is unchecked to making commission state 'Draft' than commission
        master's state will be set to 'Draft'.
        :return:
        """
        check_list = self.commission_lines_ids.mapped('paid_amount')
        if check_list and False not in check_list:
            self.status = 'Paid'
        else:
            self.status = 'Draft'

    def paid_commission(self):
        """
        This method will set all commission lines paid_amount checkbox to True
        and commission masters's state will be changed to 'Paid'.

        This method will be change state of all commissions to paid.
        :return:
        """
        self.commission_lines_ids.paid_amount = True
        self.status = 'Paid'
