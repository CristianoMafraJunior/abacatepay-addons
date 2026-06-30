# Copyright 2026 Cristiano Mafra Junior
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AbacatePay Customers",
    "summary": "Sincronização de clientes do Odoo com a AbacatePay",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Cristiano Mafra Junior, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/abacatepay-addons",
    "maintainers": ["CristianoMafraJunior"],
    "category": "Accounting/Payment",
    "depends": ["abacatepay_base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/abacatepay_export_wizard_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
}
