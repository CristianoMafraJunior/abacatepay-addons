# Copyright 2026 Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AbacatePayExportWizard(models.TransientModel):
    _name = "abacatepay.export.wizard"
    _description = "Export Contacts to AbacatePay"

    export_all = fields.Boolean(
        string="Export All Contacts with Email",
        default=True,
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Contacts",
        domain=[("email", "!=", False)],
    )
    skip_synced = fields.Boolean(
        string="Skip Already Synced",
        default=True,
        help="Do not re-sync contacts already synced with AbacatePay.",
    )

    @api.onchange("export_all")
    def _onchange_export_all(self):
        if self.export_all:
            self.partner_ids = False

    def action_export(self):
        if self.export_all:
            partners = self.env["res.partner"].search(
                [("email", "!=", False), ("active", "=", True)]
            )
        else:
            if not self.partner_ids:
                raise UserError(_("Please select at least one contact."))
            partners = self.partner_ids

        if self.skip_synced:
            partners = partners.filtered(lambda p: p.abacatepay_state != "synced")

        partners.action_abacatepay_sync()

        synced = len(partners.filtered(lambda p: p.abacatepay_state == "synced"))
        errors = len(partners.filtered(lambda p: p.abacatepay_state == "error"))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Export Complete",
                "message": f"{synced} synced, {errors} failed.",
                "type": "warning" if errors else "success",
                "sticky": bool(errors),
            },
        }
