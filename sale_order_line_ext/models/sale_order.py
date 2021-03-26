from odoo import fields, models, api, _
from functools import partial
from odoo.tools.misc import formatLang, get_lang


class SaleExt(models.Model):
    _inherit = 'sale.order'

    def update_prices(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.order_line.filtered(lambda line: not line.display_type):
            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id[0],
                line.product_tax_id, line.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update.append((1, line.id, {'price_unit': price_unit,
                                                 'discount': discount}))
        self.update({'order_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed "
                                 "according to pricelist <b>%s<b> ",
                                 self.pricelist_id.display_name))

    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env,
                          currency_obj=currency)
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.product_tax_id.compute_all(
                    price_reduce,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=order.partner_shipping_id)['taxes']
                if line.product_tax_id:
                    group = line.product_tax_id.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    if taxes:
                        if taxes['id'] == line.product_tax_id.id or taxes['id'] in \
                                line.product_tax_id.children_tax_ids.ids:
                            res[group]['amount'] += taxes['amount']
                            res[group]['base'] += taxes['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]
