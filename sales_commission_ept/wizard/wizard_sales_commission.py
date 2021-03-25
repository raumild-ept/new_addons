from odoo import fields, models, api


class ModelName(models.TransientModel):
    """
    This is wizard for model 'sales.commission.ept'. When 'Set To Draft' button
    is clicked on model 'sales.commission.ept', this wizard is used for posting the
    reason why paid order is being set to draft.
    """
    _name = 'wizard.sales.commission'
    _description = 'Wizard Sales Commission'

    reason = fields.Text(string='Enter the reason',
                         help='Enter reason for setting paid commissions to draft.')

    def post_reason(self):
        """
        When 'Change' button is clicked on this wizards form, this method is called.
        This method will notify users by posting message on 'sales.commission.ept' model.
        Than it will change state of commission to 'Draft' and it will change state of its
        commission lines to 'Draft'.

        :return:
        """
        master = self.env['sales.commission.ept'].browse(self.env.context.get('active_id'))
        master.message_post(body=self.reason, message_type='comment')
        master.status = master.commission_lines_ids.status = 'Draft'
        master.commission_lines_ids.paid_amount = False


