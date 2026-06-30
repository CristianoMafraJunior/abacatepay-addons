# Copyright 2026 Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    abacatepay_id = fields.Char(readonly=True, copy=False, index=True)
    abacatepay_state = fields.Selection(
        [("draft", "Not Synced"), ("synced", "Synced"), ("error", "Error")],
        string="AbacatePay Status",
        default="draft",
        readonly=True,
    )
    abacatepay_sync_date = fields.Datetime(string="Last Sync", readonly=True)
    abacatepay_error_message = fields.Text(string="Sync Error", readonly=True)

    def _abacatepay_headers(self):
        company = self.env.company
        api_key = company._get_abacatepay_api_key()
        if not api_key:
            raise UserError(
                f"AbacatePay API Key is not configured for company '{company.name}'."
            )
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _abacatepay_payload(self):
        self.ensure_one()
        payload = {"email": self.email}
        if self.name:
            payload["name"] = self.name
        if self.mobile or self.phone:
            payload["cellphone"] = self.mobile or self.phone
        if self.vat:
            payload["taxId"] = self.vat
        if self.zip:
            payload["zipCode"] = self.zip
        return payload

    def _abacatepay_request(self, method, endpoint, **kwargs):
        self.ensure_one()
        url = f"{self.env.company._get_abacatepay_base_url()}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self._abacatepay_headers(), timeout=30, **kwargs
            )
        except requests.exceptions.RequestException as e:
            raise UserError(f"AbacatePay connection error: {e}") from e

        if not response.ok:
            try:
                api_error = response.json().get("error") or response.text
            except Exception:
                api_error = response.text
            _logger.error(
                "AbacatePay %s %s → %s: %s",
                method,
                endpoint,
                response.status_code,
                api_error,
            )
            raise UserError(f"AbacatePay error {response.status_code}: {api_error}")

        result = response.json()
        if not result.get("success"):
            raise UserError(result.get("error") or "Unknown AbacatePay API error.")
        return result["data"]

    def action_abacatepay_sync(self):
        for partner in self:
            if not partner.email:
                partner.write(
                    {
                        "abacatepay_state": "error",
                        "abacatepay_error_message": "No email address.",
                    }
                )
                continue
            try:
                data = partner._abacatepay_request(
                    "POST", "/customers/create", json=partner._abacatepay_payload()
                )
                partner.write(
                    {
                        "abacatepay_id": data["id"],
                        "abacatepay_sync_date": fields.Datetime.now(),
                        "abacatepay_state": "synced",
                        "abacatepay_error_message": False,
                    }
                )
                _logger.info("Synced %s → %s", partner.name, data["id"])
            except UserError as e:
                partner.write(
                    {"abacatepay_state": "error", "abacatepay_error_message": str(e)}
                )
                _logger.warning("Failed to sync %s: %s", partner.name, e)
        return True

    def action_abacatepay_delete(self):
        self.ensure_one()
        if not self.abacatepay_id:
            raise UserError(_("This partner is not synced with AbacatePay."))
        self._abacatepay_request(
            "POST", "/customers/delete", params={"id": self.abacatepay_id}
        )
        self.write(
            {
                "abacatepay_id": False,
                "abacatepay_sync_date": False,
                "abacatepay_state": "draft",
                "abacatepay_error_message": False,
            }
        )
        _logger.info("Removed AbacatePay customer for %s", self.name)
