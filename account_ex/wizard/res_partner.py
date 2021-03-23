from odoo import models, fields, _


class ResPartner(models.Model):
    """
    ==> 'res.partner' model is inherited.
    """
    _inherit = 'res.partner'

    auto_validate_invoice = fields.Boolean(string='Invoice Auto Validate')

    def open_invoices(self):
        """
        ==> This method will be called when button on 'res.partner' model
            named 'Draft Invoices' will be clicked.
        :return:
        """
        invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        invoice_vals = list(map(lambda invoice: (0, 0, {'draft_invoice_id': invoice.id}), invoices))
        return {
            'name': _('Open Invoices'),
            'context': {'default_partner_id': self.id,
                        'default_draft_invoices_ids': invoice_vals},
            "view_mode": 'form',
            'res_model': 'wizard.account.move',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('account_ex.view_draft_invoices_wizard_form').id,
            'target': 'new',
        }

    def _validate_invoice(self):
        # self.env['account.move'].search([]).filtered(
        #     lambda x: x.partner_id.auto_validate_invoice == True and x.state == 'draft'
        #     and x.move_type == 'out_invoice').action_post()

        self.search([('auto_validate_invoice', '=', True)]).invoice_ids.filtered(
            lambda x: x.state == 'draft' and x.move_type == 'out_invoice').action_post()
