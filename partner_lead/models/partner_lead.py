from odoo import fields, models, api


class PartnerLead(models.Model):
    _name = 'partner.lead'

    name = fields.Char(default='SEQ_#####', readonly=True)
    from_date = fields.Date()
    to_date = fields.Date()

    partner_id = fields.Many2one(comodel_name='res.partner',
                                 domain=[('is_company', '=', True)],
                                 string='Partner')
    partner_contacts_ids = fields.Many2many(comodel_name='res.partner',
                                            string='Contacts',
                                            domain="[('is_company', '=', False), ('parent_id', '=', partner_id)]"
                                            )
    salesperson_lead_count_ids = fields.One2many(comodel_name='salesperson.count',
                                                 inverse_name='partner_id',
                                                 string='Salespersons')
    lead_ids = fields.Many2many(comodel_name='crm.lead',
                                string='Leads')
    total_revenue = fields.Float(digits=(6, 2),
                                 compute='_compute_total_revenue')

    @api.onchange('partner_id', 'partner_contacts_ids')
    def get_leads(self):
        if self.partner_id:
            leads = self.env['crm.lead'].search([('partner_id', '=', self.partner_id.id)])
            if self.partner_contacts_ids:
                leads += self.env['crm.lead'].search(
                    [('partner_id', 'in', self.partner_contacts_ids.ids)])
            lead_ids = self._get_leads_between_dates(leads)
            self.lead_ids = lead_ids

    def _get_leads_between_dates(self, leads):
        if self.from_date:
            leads = leads.filtered(lambda x: x.date_deadline >= self.from_date)
            if self.to_date:
                leads = leads.filtered(lambda x: x.date_deadline <= self.to_date)
        return leads

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('partner.lead.seq')
        return super(PartnerLead, self).create(vals_list)

    def _compute_total_revenue(self):
        for record in self:
            record.total_revenue = sum(list(map(lambda x: x.expected_revenue, record.lead_ids)))

    def get_pipeline_details(self):
        self.salesperson_lead_count_ids.unlink()
        salespersons = self.lead_ids.mapped('user_id')
        salesperson_vals = list(map(lambda sp: (0, 0, {'name': sp.id}), salespersons))
        self.write({
            'salesperson_lead_count_ids': salesperson_vals
        })
