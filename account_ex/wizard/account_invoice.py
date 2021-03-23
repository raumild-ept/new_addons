from odoo import fields, models


class Invoice(models.TransientModel):
    """
    ==> Wizard model to see draft invoices of customer and operations to validate them.
    """
    _name = 'wizard.account.move'
    _description = 'Invoices Transient'

    partner_id = fields.Many2one(comodel_name='res.partner', readonly=True)
    draft_invoices_ids = fields.One2many(comodel_name='wizard.draft.invoice',
                                         inverse_name='partner_id')

    def validate_invoices(self):
        """
        ==> This method will be called when 'Validate' button is clicked.
            It will change state of invoice from 'draft' to 'posted' whose
            checkbox is True.
        :return:
        """
        self.draft_invoices_ids.filtered(
            lambda inv: inv.validate_invoice == True).draft_invoice_id.action_post()


class DraftInvoices(models.TransientModel):
    """
    ==> Intermediate model between 'wizard.account.move' and 'account.move'
        to distinguish records with 'validate_invoice' checkbox.
    """
    _name = 'wizard.draft.invoice'

    partner_id = fields.Many2one(comodel_name='wizard.account.move',
                                 string='Customer')
    draft_invoice_id = fields.Many2one(comodel_name='account.move',
                                       string='Draft Invoice')
    validate_invoice = fields.Boolean(string='Validate')
