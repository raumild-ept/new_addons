from odoo import fields, models, api


class Project(models.Model):
    _inherit = 'project.tags'

    assigned_users = fields.Many2many(comodel_name='res.users',
                                      string='Assigned Users',
                                      compute='_compute_assigned_users')

    def _compute_assigned_users(self):
        for record in self:
            record.assigned_users = self.env['project.task'].search([('tag_ids', '=', record.id)]).user_id
