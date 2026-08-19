# Modular OS reference corpus

`Modular OS/` is the methodology and schema reference corpus used by the
module-consistency check in CI. It is not the application runtime authority.

For application execution, use the vendored Deploy V bundle at
[`caos/server/caos/methodology/vendor/deploy_v/`](../caos/server/caos/methodology/vendor/deploy_v/).
The corpus check is [`tools/check_module_consistency.py`](tools/check_module_consistency.py):

```bash
python3 "Modular OS/tools/check_module_consistency.py"
```

The [`README/`](README/) directory contains the v2 taxonomy, routing, and
onboarding references retained for that consistency check. Use those files to
review corpus alignment. Use the vendored Deploy V documentation to understand
runtime behavior and production authority.
