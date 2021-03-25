from odoo import fields, models, api


class Salesperson(models.Model):
    _name = 'salesperson.count'

    name = fields.Many2one('res.users')
    partner_id = fields.Many2one(comodel_name='partner.lead',
                                 string='Partner')
    pipelines = fields.Float(compute='_compute_fields', string='Total Pipelines')
    revenue = fields.Float(compute='_compute_fields', string='Total Revenue',
                           help='Won stages only')
    quotations = fields.Float(compute='_compute_fields', string='Total Quotations')
    sale_orders = fields.Float(compute='_compute_fields', string='Total Sale Orders')
    sale_amount = fields.Float(compute='_compute_fields', string='Total Amount')
    success_ratio = fields.Float(compute='_compute_fields',
                                 help='Success percentage of conversion from'
                                      ' expected revenue to total sale amount')

    def _compute_fields(self):
        for record in self:
            pipelines = record.partner_id.lead_ids.filtered(lambda x: x.user_id == record.name)
            record.pipelines = len(pipelines)
            record.revenue = sum(map(lambda x: x.expected_revenue, pipelines))
            record.quotations = sum(map(lambda x: x.quotation_count, pipelines))
            record.sale_orders = sum(map(lambda x: x.sale_order_count, pipelines))
            record.sale_amount = sum(map(lambda x: x.sale_amount_total, pipelines))
            record.success_ratio = record.sale_amount * 100 / record.revenue if record.revenue is not 0 else 100
