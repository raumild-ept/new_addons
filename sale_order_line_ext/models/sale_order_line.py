from odoo import fields, models, api
from odoo.tools.misc import get_lang


class SaleOrderLineExt(models.Model):
    _inherit = 'sale.order.line'

    product_tax_id = fields.Many2one(comodel_name='account.tax',
                                     string='Tax',
                                     domain=['|', ('active', '=', False),
                                             ('active', '=', True)])

    def _compute_tax_id(self):
        line = 0
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or \
                   line.order_id.fiscal_position_id.get_fiscal_position(
                       line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda t: t.company_id == line.env.company)
            if taxes:
                line.product_tax_id = fpos.map_tax(
                    taxes[0],
                    line.product_id,
                    line.order_id.partner_shipping_id)

    @api.depends('product_uom_qty', 'discount',
                 'price_unit', 'product_tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.product_tax_id.compute_all(price, line.order_id.currency_id,
                                                    line.product_uom_qty,
                                                    product=line.product_id,
                                                    partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.product_tax_id.invalidate_cache(['invoice_repartition_line_ids'],
                                                     [line.product_tax_id.id])

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or \
                   line.order_id.fiscal_position_id.get_fiscal_position(
                       line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
            line.product_tax_id = fpos.map_tax(
                taxes[0],
                line.product_id,
                line.order_id.partner_shipping_id)

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name', 'price_unit', 'product_uom', 'product_tax_id']
        if values.get('order_id') and values.get('product_id') and \
                any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.product_id_change()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        return res

    @api.depends('state', 'price_reduce', 'product_id',
                 'untaxed_amount_invoiced', 'qty_delivered',
                 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on
         the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice
             policy of the product.

            Note: Draft invoice are ignored on purpose,
             the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use price_subtotal field as it returns
                # zero when the ordered quantity is
                # zero. It causes problem for expense line
                # (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but
                # when you can invoice the line, you see an
                # amount and not zero. Since we compute
                # untaxed amount, we can use directly the price
                # reduce (to include discount) without
                # using `compute_all()` method on taxes.
                price_subtotal = 0.0
                if line.product_id.invoice_policy == 'delivery':
                    price_subtotal = line.price_reduce * line.qty_delivered
                else:
                    price_subtotal = line.price_reduce * line.product_uom_qty
                if line.product_tax_id.price_include > 0:
                    # As included taxes are not excluded from the computed subtotal,
                    # `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from
                    # `price_subtotal` field. (see upper Note)
                    price_subtotal = line.product_tax_id.compute_all(
                        price_subtotal,
                        currency=line.order_id.currency_id,
                        quantity=line.product_uom_qty,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id)['total_excluded']

                if any(line.invoice_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in line.invoice_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(
                                l.currency_id._convert(
                                    l.price_unit, line.currency_id, line.company_id,
                                    l.date or fields.Date.today(),
                                    round=False) * l.quantity)['total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit,
                                                             line.currency_id,
                                                             line.company_id,
                                                             l.date or fields.Date.today(),
                                                             round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal - amount, 0)
                else:
                    amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced

            line.untaxed_amount_to_invoice = amount_to_invoice

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new
         invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added
                                to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, [self.product_tax_id.id])],
            'analytic_account_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id. \
            valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id[0],
                self.product_tax_id, self.company_id)
        self.update(vals)
        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result

    def _get_protected_fields(self):
        return [
            'product_id', 'name', 'price_unit',
            'product_uom', 'product_uom_qty',
            'product_tax_id', 'analytic_tag_ids'
        ]

    @api.onchange('product_id', 'price_unit', 'product_uom',
                  'product_uom_qty', 'product_tax_id')
    def _onchange_discount(self):
        if not (self.product_id and self.product_uom and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context,
                               partner_id=self.order_id.partner_id.id,
                               date=self.order_id.date_order,
                               uom=self.product_uom.id)

        price, rule_id = self.order_id.pricelist_id. \
            with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context). \
            _get_real_price_currency(product, rule_id,
                                     self.product_uom_qty,
                                     self.product_uom,
                                     self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as
                # price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and
                                                         new_list_price < 0):
                self.discount = discount
