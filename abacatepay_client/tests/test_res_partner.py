# Copyright 2026 Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

PATCH_REQUESTS = "odoo.addons.abacatepay_client.models.res_partner.requests.request"


def _mock_response(json_data, status_code=200, ok=True):
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = ok
    mock.json.return_value = json_data
    mock.text = str(json_data)
    return mock


class TestAbacatePayPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.company.abacatepay_api_key = "test-api-key"
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
                "phone": "+5511999999999",
                "vat": "123.456.789-01",
                "zip": "01310-100",
            }
        )

    def test_payload_includes_all_fields(self):
        payload = self.partner._abacatepay_payload()
        self.assertEqual(payload["email"], "test@example.com")
        self.assertEqual(payload["name"], "Test Partner")
        self.assertEqual(payload["cellphone"], "+5511999999999")
        self.assertEqual(payload["taxId"], "123.456.789-01")
        self.assertEqual(payload["zipCode"], "01310-100")

    def test_payload_email_only(self):
        partner = self.env["res.partner"].create(
            {"name": "Minimal", "email": "minimal@example.com"}
        )
        payload = partner._abacatepay_payload()
        self.assertIn("email", payload)
        self.assertNotIn("cellphone", payload)
        self.assertNotIn("taxId", payload)
        self.assertNotIn("zipCode", payload)

    def test_payload_prefers_mobile_over_phone(self):
        self.partner.mobile = "+5511888888888"
        payload = self.partner._abacatepay_payload()
        self.assertEqual(payload["cellphone"], "+5511888888888")

    def test_headers_with_api_key(self):
        headers = self.partner._abacatepay_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-api-key")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_headers_missing_api_key_raises(self):
        self.env.company.abacatepay_api_key = False
        with self.assertRaises(UserError):
            self.partner._abacatepay_headers()

    @patch(PATCH_REQUESTS)
    def test_sync_success(self, mock_request):
        mock_request.return_value = _mock_response(
            {"success": True, "data": {"id": "cust_abc123"}}
        )
        self.partner.action_abacatepay_sync()
        self.assertEqual(self.partner.abacatepay_id, "cust_abc123")
        self.assertEqual(self.partner.abacatepay_state, "synced")
        self.assertFalse(self.partner.abacatepay_error_message)
        self.assertTrue(self.partner.abacatepay_sync_date)

    @patch(PATCH_REQUESTS)
    def test_sync_no_email_skips_api_call(self, mock_request):
        partner = self.env["res.partner"].create({"name": "No Email"})
        partner.action_abacatepay_sync()
        mock_request.assert_not_called()
        self.assertEqual(partner.abacatepay_state, "error")

    @patch(PATCH_REQUESTS)
    def test_sync_api_returns_error(self, mock_request):
        mock_request.return_value = _mock_response(
            {"error": "Invalid email"}, status_code=422, ok=False
        )
        self.partner.action_abacatepay_sync()
        self.assertEqual(self.partner.abacatepay_state, "error")
        self.assertIn("422", self.partner.abacatepay_error_message)

    @patch(PATCH_REQUESTS)
    def test_sync_connection_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError("timeout")
        self.partner.action_abacatepay_sync()
        self.assertEqual(self.partner.abacatepay_state, "error")
        self.assertIn("connection error", self.partner.abacatepay_error_message.lower())

    @patch(PATCH_REQUESTS)
    def test_sync_batch_continues_on_error(self, mock_request):
        partner_ok = self.env["res.partner"].create(
            {"name": "OK", "email": "ok@example.com"}
        )
        partner_fail = self.env["res.partner"].create(
            {"name": "Fail", "email": "fail@example.com"}
        )

        def side_effect(*args, **kwargs):
            payload = kwargs.get("json", {})
            if payload.get("email") == "fail@example.com":
                return _mock_response({"error": "rejected"}, status_code=400, ok=False)
            return _mock_response({"success": True, "data": {"id": "cust_ok"}})

        mock_request.side_effect = side_effect

        (partner_ok | partner_fail).action_abacatepay_sync()

        self.assertEqual(partner_ok.abacatepay_state, "synced")
        self.assertEqual(partner_fail.abacatepay_state, "error")

    def test_delete_not_synced_raises(self):
        with self.assertRaises(UserError):
            self.partner.action_abacatepay_delete()

    @patch(PATCH_REQUESTS)
    def test_delete_success_resets_fields(self, mock_request):
        self.partner.write(
            {"abacatepay_id": "cust_abc123", "abacatepay_state": "synced"}
        )
        mock_request.return_value = _mock_response({"success": True, "data": {}})

        self.partner.action_abacatepay_delete()

        self.assertFalse(self.partner.abacatepay_id)
        self.assertFalse(self.partner.abacatepay_sync_date)
        self.assertEqual(self.partner.abacatepay_state, "draft")
        self.assertFalse(self.partner.abacatepay_error_message)

    @patch(PATCH_REQUESTS)
    def test_delete_calls_correct_endpoint(self, mock_request):
        self.partner.write(
            {"abacatepay_id": "cust_abc123", "abacatepay_state": "synced"}
        )
        mock_request.return_value = _mock_response({"success": True, "data": {}})

        self.partner.action_abacatepay_delete()

        call_kwargs = mock_request.call_args
        self.assertIn("/customers/delete", call_kwargs[0][1])
        self.assertEqual(call_kwargs[1]["params"]["id"], "cust_abc123")
