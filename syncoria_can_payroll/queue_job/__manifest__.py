# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "Job Queue",
    "version": "17.0.1.0.6",
    "author": "Camptocamp,ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/queue",
    "license": "LGPL-3",
    "category": "Generic Modules",
    "depends": ["mail", "base_sparse_field", "web"],
    "external_dependencies": {"python": ["requests"]},
    "data": [],
    "assets": {
        "web.assets_backend": [
            "/queue_job/static/src/views/**/*",
        ],
    },
    "installable": True,
    "development_status": "Mature",
    "maintainers": ["guewen"],
    "post_init_hook": "post_init_hook",
    "post_load": "post_load",
}
