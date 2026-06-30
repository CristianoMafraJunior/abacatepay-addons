# Copyright 2026 Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

ABACATEPAY_API_BASE_URL = "https://api.abacatepay.com/v2"


class ResCompany(models.Model):
    _inherit = "res.company"

    abacatepay_api_key = fields.Char(
        string="API Key",
    )
    abacatepay_dev_mode = fields.Boolean(
        string="Sandbox Mode",
        help="Enable to use the AbacatePay sandbox environment "
        "and simulate payments without real charges.",
    )

    def _get_abacatepay_api_key(self):
        self.ensure_one()
        return self.sudo().abacatepay_api_key

    def _get_abacatepay_base_url(self):
        return ABACATEPAY_API_BASE_URL
