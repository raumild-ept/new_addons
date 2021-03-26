from odoo import models
from odoo.exceptions import UserError


class AccountMoveExt(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        # inherit of the function from account.move to validate
        # a new tax and the priceunit of a downpayment
        res = super(AccountMoveExt, self).action_post()
        line_ids = self.mapped('line_ids').filtered(
            lambda line: line.sale_line_ids.is_downpayment)
        for line in line_ids:
            try:
                line.sale_line_ids.product_tax_id = line.tax_ids
                # To keep positive amount on the sale order and
                # to have the right price for the invoice
                # We need the - before our untaxed_amount_to_invoice
                line.sale_line_ids.price_unit = -line.sale_line_ids.untaxed_amount_to_invoice
            except UserError:
                # a UserError here means the SO was locked,
                # which prevents changing the taxes
                # just ignore the error - this is a nice
                # to have feature and should not be blocking
                pass
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _sale_prepare_sale_line_values(self, order, price):
        """ Generate the sale.line creation value from the current move line """
        self.ensure_one()
        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)],
                                                          order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.fiscal_position_id. \
            get_fiscal_position(order.partner_id.id)
        taxes = fpos.map_tax(self.product_id.taxes_id,
                             self.product_id, order.partner_id)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'product_tax_id': taxes.id,
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'is_expense': True,
        }
